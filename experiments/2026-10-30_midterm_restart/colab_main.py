"""Frozen representative main30, then fixed April/May evaluation. No tuning."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import argparse
import copy
import fcntl
import gc
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback
import zipfile
import numpy as np
import torch
from data import HERE, digest, load_config, read_split, save_npz, write_json
from models import make_model, statistics
from training import fit_network, fit_m0, hash_bytes, load_checkpoint, metrics

TRAIN=HERE/'main_training'
EVAL=HERE/'main_evaluation'
SOURCE=['config.json','main_frozen.json','data.py','models.py','training.py','colab_main.py']

def frozen_config():
    f=json.loads((HERE/'main_frozen.json').read_text())
    cfg=load_config()
    if digest(HERE/'config.json')!=f['base_config_sha256'] or not f['epochs_frozen']:
        raise ValueError('Frozen protocol/base configuration mismatch')
    if (f['epochs'],f['budget'],f['cohort'],f['seeds'],f['planned_fits']) != (50,200,'google_included20',[201,202,203,204,205],30):
        raise ValueError('Outside approved representative scope')
    cfg=copy.deepcopy(cfg)
    cfg['training']['epochs_frozen']=True
    return cfg,f

def pack(folder, name):
    paths=[p for p in sorted(folder.rglob('*')) if p.is_file() and p.suffix!='.tmp' and p.name not in ['file_hashes.json','runner.lock']]
    paths += [HERE/p for p in SOURCE]
    write_json(folder/'file_hashes.json',{str(p.relative_to(HERE)):digest(p) for p in paths})
    paths.append(folder/'file_hashes.json')
    target=HERE/name;tmp=target.with_suffix('.tmp')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for p in paths:z.write(p,str(p.relative_to(HERE)))
    tmp.replace(target)
    record=dict(path=str(target),bytes=target.stat().st_size,sha256=digest(target))
    write_json(HERE/(name+'.json'),record)
    print('ARCHIVE',json.dumps(record),flush=True)

def compact_metrics(y,pred,true_logp,classes):
    if len(y)==0:
        return dict(n=0,macro_f1=None,accuracy=None,gt_cross_entropy=None,support=[0]*classes,
                    per_class_f1=[None]*classes,per_class_precision=[None]*classes,per_class_recall=[None]*classes,
                    classes_with_support=0,confusion=np.zeros((classes,classes),dtype=int).tolist())
    cm=np.bincount(y.astype('i8')*classes+pred,minlength=classes*classes).reshape(classes,classes)
    support=cm.sum(1); predicted=cm.sum(0); tp=np.diag(cm)
    ratio=lambda n,d:np.divide(n,d,out=np.zeros(classes,dtype='f8'),where=d>0).tolist()
    f1=ratio(2*tp,support+predicted)
    return dict(n=len(y),macro_f1=float(np.mean(f1)),accuracy=float(tp.sum()/len(y)),
                gt_cross_entropy=float(-np.mean(true_logp,dtype='f8')),support=support.tolist(),
                per_class_f1=f1,per_class_precision=ratio(tp,predicted),per_class_recall=ratio(tp,support),
                classes_with_support=int((support>0).sum()),confusion=cm.tolist())

def run(minutes):
    cfg,f=frozen_config()
    if not torch.cuda.is_available():raise RuntimeError('CUDA required; refuse CPU neural training')
    TRAIN.mkdir(exist_ok=True);EVAL.mkdir(exist_ok=True)
    lock=(TRAIN/'runner.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    start=time.monotonic(); deadline=start+minutes*60
    freeze_sha=digest(HERE/'main_frozen.json')
    runtime=dict(pid=os.getpid(),started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),device=torch.cuda.get_device_name(0),
                 python=platform.python_version(),packages={p:importlib.metadata.version(p) for p in ['torch','numpy','cesnet-models','lightgbm']},
                 cuda=torch.version.cuda,time_limit_minutes=minutes,precision='FP32; TF32 disabled; batch128',
                 base_config_sha256=digest(HERE/'config.json'),frozen_settings_sha256=freeze_sha,planned_fits=30,
                 source_hashes={p:digest(HERE/p) for p in SOURCE},scope='Main budget200 only; no search; April/May after all checkpoints frozen')
    rp=TRAIN/'runtime.json'
    if not rp.exists():write_json(rp,runtime)
    else:write_json(TRAIN/f'resume_{os.getpid()}.json',runtime)
    for cmd,name in [([sys.executable,'-m','pip','freeze'],'pip_freeze.txt'),(['nvidia-smi'],'nvidia_smi.txt')]:
        (TRAIN/name).write_text(subprocess.run(cmd,capture_output=True,text=True,check=True).stdout)
    done=[]; evaluations=[]; checkpoints={}
    def status(state,current=None):
        write_json(HERE/'main_status.json',dict(state=state,current=current,completed=len(done),planned=30,
                   evaluations_completed=len(evaluations),evaluations_planned=60,elapsed_seconds=time.monotonic()-start,
                   started_utc=runtime['started_utc'],completed_runs=done,evaluations=evaluations))
    def budget():
        if time.monotonic()>deadline-30:raise TimeoutError('Budget stop; preserve partial results')
    cohort=f['cohort'];val=read_split(cohort,'validation');classes=len(cfg['cohorts'][cohort]['classes'])
    try:
        for seed in f['seeds']:
            train=read_split(cohort,f'main_seed{seed}',f['budget'])
            for kind in ['M0','M1','M2','M3','M4','M5']:
                budget();name=f'{kind}_s{seed}_n200';out=TRAIN/'fits'/name;out.mkdir(parents=True,exist_ok=True)
                choice=f['selected'].get(kind,f['selected']['M3'])
                alpha=f['kd']['alpha'] if kind in ['M4','M5'] else 0.
                temperature=f['kd']['temperature'] if kind in ['M4','M5'] else 1
                context=dict(model=kind,seed=seed,budget=200,phase='main',cohort=cohort,classes=cfg['cohorts'][cohort]['classes'],
                             frozen_settings_sha256=freeze_sha,choice=choice,alpha=alpha,temperature=temperature,
                             train_ids_sha256=hash_bytes(train['id']),train_input_sha256=hash_bytes(train['X']),
                             train_labels_sha256=hash_bytes(train['y']),validation_ids_sha256=hash_bytes(val['id']))
                cp=out/('best.txt' if kind=='M0' else 'best.pt');mp=out/'metrics.json'
                if (out/'run_context.json').exists():
                    if json.loads((out/'run_context.json').read_text())!=context:raise ValueError('Existing fit context differs')
                else:write_json(out/'run_context.json',context)
                status('training',name)
                if mp.exists():
                    m=json.loads(mp.read_text())
                    if digest(cp)!=m['best_checkpoint_sha256']:raise ValueError('Existing checkpoint corrupt')
                else:
                    gc.collect();torch.cuda.empty_cache();torch.cuda.reset_peak_memory_stats()
                    t=time.perf_counter();wall=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
                    if kind=='M0':model,m=fit_m0(train,val,cfg,out,seed,num_leaves=int(choice))
                    else:
                        teacher=checkpoints.get(('M1' if kind=='M4' else 'M2',seed)) if kind in ['M4','M5'] else None
                        model,m=fit_network(kind,train,val,cfg,out,cohort,seed,200,choice,f['epochs'],device='cuda',
                            teacher_checkpoint=teacher,alpha=alpha,temperature=temperature,phase='main',
                            time_limit=max(1,deadline-time.monotonic()-30),resume_from=(out/'last.pt') if (out/'last.pt').exists() else None)
                    write_json(out/'resources.json',dict(started_utc=wall,ended_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                              full_fit_seconds=time.perf_counter()-t,cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                              cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved(),includes='model init + teacher prediction + fitting/validation + checkpoint I/O; excludes archive'))
                    del model;gc.collect();torch.cuda.empty_cache()
                checkpoints[kind,seed]=cp;done.append(name);status('training',name)
                write_json(TRAIN/'status.json',dict(state='training',completed=len(done),planned=30))
                pack(TRAIN,'main_training_results.zip')
        frozen={f'{m}_s{s}_n200':digest(p) for (m,s),p in checkpoints.items()}
        write_json(TRAIN/'frozen_checkpoints.json',dict(frozen_before_evaluation_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                   frozen_settings_sha256=freeze_sha,checkpoints=frozen,selection='February only; no April/May scores used'))
        write_json(TRAIN/'status.json',dict(state='completed',completed=30,planned=30,elapsed_seconds=time.monotonic()-start))
        pack(TRAIN,'main_training_results.zip')
        # Training ZIP stays immutable throughout evaluation, allowing early recovery.
        for month in f['evaluation_months']:
            data=read_split(cohort,f'evaluation_{month}');groups=read_split(cohort,f'evaluation_groups_{month}')
            if not np.array_equal(data['id'],groups['id']):raise ValueError('Evaluation IDs/masks differ')
            for seed in f['seeds']:
                overlap=groups[f'seed{seed}_n200_train_overlap']; unseen=groups['common_unseen']
                if np.any(overlap&unseen):raise ValueError('Invalid overlap groups')
                masks=dict(all=np.ones(len(overlap),bool),train_overlap=overlap,train_nonoverlap=~overlap,common_unseen=unseen)
                for kind in ['M0','M1','M2','M3','M4','M5']:
                    budget();name=f'{kind}_s{seed}_n200';key=f'{month}/{name}';out=EVAL/month/name;out.mkdir(parents=True,exist_ok=True)
                    cp=checkpoints[kind,seed];cp_sha=digest(cp)
                    if cp_sha!=frozen[name]:raise ValueError('Checkpoint changed after freeze')
                    status('evaluating',key)
                    if (out/'metrics.json').exists():
                        old=json.loads((out/'metrics.json').read_text())
                        if old['checkpoint_sha256']!=cp_sha or old['prediction_sha256']!=digest(out/'predictions.npz'):raise ValueError('Evaluation resume differs')
                    else:
                        gc.collect();torch.cuda.empty_cache();torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
                        if kind=='M0':
                            import lightgbm as lgb
                            model=lgb.Booster(model_file=str(cp))
                        else:
                            model=make_model(kind,classes,seed,cfg,load_pretrained=False).to('cuda');load_checkpoint(cp,model);model.eval()
                        n=len(data['id']);pred=np.empty(n,dtype='u1');lp=np.empty(n,dtype='f4');confidence=np.empty(n,dtype='f4')
                        batch=f['evaluation']['batch_size']
                        for offset in range(0,n,batch):
                            budget();end=min(n,offset+batch);x=data['X'][offset:end];y=data['y'][offset:end]
                            if kind=='M0':
                                prob=model.predict(statistics(x)[0],num_threads=1);pred[offset:end]=prob.argmax(1)
                                confidence[offset:end]=prob.max(1);lp[offset:end]=np.log(np.clip(prob[np.arange(len(y)),y],1e-30,1))
                            else:
                                with torch.inference_mode():
                                    logp=model(torch.as_tensor(x,dtype=torch.float32,device='cuda')).log_softmax(1).cpu()
                                if not torch.isfinite(logp).all():raise FloatingPointError('Invalid log probabilities')
                                pred[offset:end]=logp.argmax(1).numpy();confidence[offset:end]=logp.max(1).values.exp().numpy()
                                lp[offset:end]=logp[torch.arange(len(y)),torch.as_tensor(y,dtype=torch.long)].numpy()
                        scores={k:compact_metrics(data['y'][mask],pred[mask],lp[mask],classes) for k,mask in masks.items()}
                        save_npz(out/'predictions.npz',id=data['id'],y=data['y'].astype('u1'),predicted_label=pred,true_log_probability=lp,maximum_probability=confidence)
                        write_json(out/'metrics.json',dict(model=kind,seed=seed,budget=200,month=month,phase='evaluation',classes=cfg['cohorts'][cohort]['classes'],
                            checkpoint_sha256=cp_sha,frozen_settings_sha256=freeze_sha,evaluation_ids_sha256=hash_bytes(data['id']),
                            evaluation_input_sha256=hash_bytes(data['X']),evaluation_labels_sha256=hash_bytes(data['y']),
                            prediction_sha256=digest(out/'predictions.npz'),groups=scores,seconds=time.perf_counter()-t,
                            cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(),device='cpu1' if kind=='M0' else 'cuda',
                            prediction_storage=f['evaluation']['compact_prediction_storage'],note='Full class probability vectors not retained; exact checkpoints and inputs retained. CE from saved float32 log p(true).'))
                        del model;gc.collect();torch.cuda.empty_cache()
                    evaluations.append(key);status('evaluating',key)
                    # Small evaluation archive, separate from all resumable training state.
                    write_json(EVAL/'status.json',dict(state='evaluating',completed=len(evaluations),planned=60))
                    pack(EVAL,'main_evaluation_results.zip')
        status('completed');write_json(EVAL/'status.json',dict(state='completed',completed=60,planned=60,elapsed_seconds=time.monotonic()-start))
        pack(EVAL,'main_evaluation_results.zip')
    except BaseException as e:
        status('budget_stopped' if isinstance(e,TimeoutError) else 'failed')
        write_json(HERE/'main_failure.json',dict(type=type(e).__name__,message=str(e),traceback=traceback.format_exc()))
        if len(done)<30:pack(TRAIN,'main_training_results.zip')
        pack(EVAL,'main_evaluation_results.zip')
        raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--minutes',type=float,default=45);a=p.parse_args()
    if not 1<=a.minutes<=45:p.error('Limit must be1..45 minutes')
    run(a.minutes)
