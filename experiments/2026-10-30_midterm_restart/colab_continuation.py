"""Frozen, bounded continuation: label curve and representative cohort comparisons.
Reuses unchanged fitting code. Completed stage archives never change.
"""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import argparse,copy,fcntl,gc,importlib.metadata,json,platform,subprocess,sys,time,traceback,zipfile
from datetime import datetime,timezone,timedelta
from pathlib import Path
import numpy as np
import torch
from data import HERE,digest,read_split,save_npz,write_json
from models import make_model,statistics
from training import fit_network,fit_m0,hash_bytes,load_checkpoint
from colab_main import frozen_config,compact_metrics

BASE=HERE/'continuation';ARCHIVES=HERE/'continuation_archives'
SOURCE=['config.json','main_frozen.json','continuation_frozen.json','data.py','models.py','training.py','colab_main.py','colab_continuation.py']

def settings():
    cfg,base=frozen_config();plan=json.loads((HERE/'continuation_frozen.json').read_text())
    expected=[('mixed_n50','google_included20',50),('mixed_n100','google_included20',100),('mixed_n1000','google_included20',1000),('nongoogle_n200','non_google13',200),('googleonly_n200','google_only20',200)]
    if [(s['id'],s['cohort'],s['budget'])for s in plan['stages']]!=expected:raise ValueError('Unapproved stage list')
    if plan['main_frozen_sha256']!=digest(HERE/'main_frozen.json') or plan['seeds']!=base['seeds'] or plan['planned_fits']!=150:raise ValueError('Protocol mismatch')
    for name,h in plan['core_source_sha256'].items():
        if digest(HERE/name)!=h:raise ValueError('Core source changed: '+name)
    return cfg,base,plan

def pack(folder,stage,kind):
    ARCHIVES.mkdir(exist_ok=True)
    paths=[p for p in sorted(folder.rglob('*'))if p.is_file() and p.suffix!='.tmp' and p.name!='file_hashes.json']
    paths += [HERE/n for n in SOURCE]
    write_json(folder/'file_hashes.json',{str(p.relative_to(HERE)):digest(p)for p in paths})
    paths.append(folder/'file_hashes.json')
    dst=ARCHIVES/f'{stage}_{kind}.zip';tmp=dst.with_suffix('.tmp')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED,compresslevel=1)as z:
        for p in paths:z.write(p,str(p.relative_to(HERE)))
    tmp.replace(dst)
    rec=dict(stage=stage,kind=kind,path=str(dst),bytes=dst.stat().st_size,sha256=digest(dst))
    write_json(dst.with_suffix('.zip.json'),rec)
    print('ARCHIVE',json.dumps(rec),flush=True)
    return rec

def eval_one(kind,seed,budget,cohort,cp,out,cfg,base,freeze_sha,data,groups,features,check_budget):
    cp_sha=digest(cp);C=len(cfg['cohorts'][cohort]['classes'])
    ident=dict(model=kind,seed=seed,budget=budget,cohort=cohort,phase='evaluation',classes=cfg['cohorts'][cohort]['classes'],
        checkpoint_sha256=cp_sha,frozen_settings_sha256=freeze_sha,evaluation_ids_sha256=hash_bytes(data['id']),
        evaluation_input_sha256=hash_bytes(data['X']),evaluation_labels_sha256=hash_bytes(data['y']))
    if (out/'metrics.json').exists():
        old=json.loads((out/'metrics.json').read_text())
        if any(old[k]!=v for k,v in ident.items())or old['prediction_sha256']!=digest(out/'predictions.npz'):raise ValueError('Evaluation resume mismatch')
        return
    out.mkdir(parents=True,exist_ok=True);gc.collect();torch.cuda.empty_cache();torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
    if kind=='M0':
        import lightgbm as lgb
        model=lgb.Booster(model_file=str(cp))
    else:
        model=make_model(kind,C,seed,cfg,load_pretrained=False).to('cuda');load_checkpoint(cp,model);model.eval()
    n=len(data['id']);pred=np.empty(n,dtype='u1');lp=np.empty(n,dtype='f4');confidence=np.empty(n,dtype='f4')
    for offset in range(0,n,base['evaluation']['batch_size']):
        check_budget();end=min(n,offset+base['evaluation']['batch_size']);x=data['X'][offset:end];y=data['y'][offset:end]
        if kind=='M0':
            prob=model.predict(features[offset:end],num_threads=1);pred[offset:end]=prob.argmax(1);confidence[offset:end]=prob.max(1)
            lp[offset:end]=np.log(np.clip(prob[np.arange(len(y)),y],1e-30,1))
        else:
            with torch.inference_mode():logp=model(torch.as_tensor(x,dtype=torch.float32,device='cuda')).log_softmax(1).cpu()
            if not torch.isfinite(logp).all():raise FloatingPointError('Invalid evaluation logits')
            pred[offset:end]=logp.argmax(1).numpy();confidence[offset:end]=logp.max(1).values.exp().numpy()
            lp[offset:end]=logp[torch.arange(len(y)),torch.as_tensor(y,dtype=torch.long)].numpy()
    overlap=groups[f'seed{seed}_n{budget}_train_overlap'];unseen=groups['common_unseen']
    if np.any(overlap&unseen):raise ValueError('Invalid evaluation masks')
    masks=dict(all=np.ones(n,bool),train_overlap=overlap,train_nonoverlap=~overlap,common_unseen=unseen)
    scores={k:compact_metrics(data['y'][m],pred[m],lp[m],C)for k,m in masks.items()}
    save_npz(out/'predictions.npz',id=data['id'],y=data['y'].astype('u1'),predicted_label=pred,true_log_probability=lp,maximum_probability=confidence)
    write_json(out/'metrics.json',dict(**ident,month=out.parent.name,prediction_sha256=digest(out/'predictions.npz'),groups=scores,
        seconds=time.perf_counter()-t,cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(),device='cpu1'if kind=='M0'else'cuda',
        prediction_storage=base['evaluation']['compact_prediction_storage'],feature_cache='Exact unchanged statistics; calculated once per cohort/month; no fitting or labels used'))
    del model;gc.collect();torch.cuda.empty_cache()

def run(minutes):
    cfg,f,plan=settings()
    if not torch.cuda.is_available():raise RuntimeError('CUDA required; no CPU neural fitting')
    BASE.mkdir(exist_ok=True);ARCHIVES.mkdir(exist_ok=True)
    lock=(BASE/'runner.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    start=time.monotonic();deadline=start+minutes*60;freeze_sha=digest(HERE/'continuation_frozen.json')
    runtime=dict(pid=os.getpid(),started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),device=torch.cuda.get_device_name(0),
        python=platform.python_version(),packages={p:importlib.metadata.version(p)for p in ['torch','numpy','cesnet-models','lightgbm']},cuda=torch.version.cuda,
        time_limit_minutes=minutes,frozen_settings_sha256=freeze_sha,source_hashes={p:digest(HERE/p)for p in SOURCE},planned_fits=150,planned_evaluations=250,local_m0_evaluations_planned=50)
    write_json(BASE/('runtime.json'if not(BASE/'runtime.json').exists()else f'resume_{os.getpid()}.json'),runtime)
    for cmd,n in [([sys.executable,'-m','pip','freeze'],'pip_freeze.txt'),(['nvidia-smi'],'nvidia_smi.txt')]:
        (BASE/n).write_text(subprocess.run(cmd,capture_output=True,text=True,check=True).stdout)
    done=[];evdone=[];finished=[];archives=[];current=None;stage=None
    def status(state):
        write_json(BASE/'status.json',dict(state=state,current=current,completed=len(done),planned=150,evaluations_completed=len(evdone),evaluations_planned=250,local_m0_evaluations_planned=50,
            elapsed_seconds=time.monotonic()-start,started_utc=runtime['started_utc'],deadline_utc=(datetime.fromisoformat(runtime['started_utc'].replace('Z','+00:00'))+timedelta(minutes=minutes)).isoformat(),time_limit_minutes=minutes,
            completed_runs=done,evaluations=evdone,finished_stages=finished,archives=archives))
    def check_budget():
        if time.monotonic()>deadline-60:raise TimeoutError('Bounded session ended; last checkpoint preserved')
    try:
        for stage in plan['stages']:
            sid,cohort,budget=stage['id'],stage['cohort'],stage['budget'];root=BASE/sid;tr=root/'training';ev=root/'evaluation';tr.mkdir(parents=True,exist_ok=True);ev.mkdir(exist_ok=True)
            # Reusing a complete stage must not rewrite its frozen timestamp or ZIP.
            stage_archives=[]
            for kind in ['training','evaluation']:
                ap=ARCHIVES/f'{sid}_{kind}.zip';meta=ap.with_suffix('.zip.json')
                st=root/kind/'status.json'
                if meta.exists() and ap.exists() and st.exists() and json.loads(st.read_text())['state']=='completed':
                    rec=json.loads(meta.read_text())
                    if digest(ap)!=rec['sha256']:raise ValueError('Completed archive corrupt')
                    stage_archives.append(rec)
            if len(stage_archives)==2:
                frozen_old=json.loads((tr/'frozen_checkpoints.json').read_text())
                if frozen_old['frozen_settings_sha256']!=freeze_sha:raise ValueError('Completed protocol differs')
                archives.extend(stage_archives)
                done.extend(f'{sid}/training/{m}_s{s}_n{budget}'for s in plan['seeds']for m in ['M0','M1','M2','M3','M4','M5'])
                evdone.extend(f'{sid}/{month}/{m}_s{s}_n{budget}'for month in f['evaluation_months']for s in plan['seeds']for m in ['M1','M2','M3','M4','M5'])
                finished.append(sid);status('stage_reused');continue
            for n in ['runtime.json','pip_freeze.txt','nvidia_smi.txt']:
                if not(tr/n).exists():(tr/n).write_bytes((BASE/n).read_bytes())
            val=read_split(cohort,'validation');checkpoints={}
            for seed in plan['seeds']:
                train=read_split(cohort,f'main_seed{seed}',budget)
                for kind in ['M0','M1','M2','M3','M4','M5']:
                    check_budget();name=f'{kind}_s{seed}_n{budget}';current=f'{sid}/training/{name}';out=tr/'fits'/name;out.mkdir(parents=True,exist_ok=True)
                    choice=f['selected'].get(kind,f['selected']['M3']);alpha=f['kd']['alpha']if kind in ['M4','M5']else 0.;temperature=f['kd']['temperature']if kind in ['M4','M5']else 1
                    context=dict(stage=sid,cohort=cohort,model=kind,seed=seed,budget=budget,phase='main',classes=cfg['cohorts'][cohort]['classes'],
                        frozen_settings_sha256=freeze_sha,choice=choice,alpha=alpha,temperature=temperature,train_ids_sha256=hash_bytes(train['id']),
                        train_input_sha256=hash_bytes(train['X']),train_labels_sha256=hash_bytes(train['y']),validation_ids_sha256=hash_bytes(val['id']))
                    cp=out/('best.txt'if kind=='M0'else'best.pt');mp=out/'metrics.json'
                    if(out/'run_context.json').exists():
                        if json.loads((out/'run_context.json').read_text())!=context:raise ValueError('Existing context mismatch')
                    else:write_json(out/'run_context.json',context)
                    status('training')
                    if mp.exists():
                        m=json.loads(mp.read_text())
                        if digest(cp)!=m['best_checkpoint_sha256']:raise ValueError('Existing checkpoint corrupt')
                    else:
                        gc.collect();torch.cuda.empty_cache();torch.cuda.reset_peak_memory_stats();t=time.perf_counter();wall=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
                        if kind=='M0':model,m=fit_m0(train,val,cfg,out,seed,num_leaves=int(choice))
                        else:
                            teacher=checkpoints.get(('M1'if kind=='M4'else'M2',seed))if kind in ['M4','M5']else None
                            model,m=fit_network(kind,train,val,cfg,out,cohort,seed,budget,choice,f['epochs'],device='cuda',teacher_checkpoint=teacher,
                                alpha=alpha,temperature=temperature,phase='main',time_limit=max(1,deadline-time.monotonic()-60),
                                resume_from=out/'last.pt'if(out/'last.pt').exists()else None)
                        write_json(out/'resources.json',dict(started_utc=wall,ended_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),full_fit_seconds=time.perf_counter()-t,
                            cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(),cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved()))
                        del model;gc.collect();torch.cuda.empty_cache()
                    checkpoints[kind,seed]=cp;done.append(current);status('training')
            frozen={f'{m}_s{s}_n{budget}':digest(p)for(m,s),p in checkpoints.items()}
            frozen_record=dict(frozen_before_evaluation_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),frozen_settings_sha256=freeze_sha,
                checkpoints=frozen,selection='February only; unchanged settings from representative budget200 development')
            fp=tr/'frozen_checkpoints.json'
            if fp.exists():
                old=json.loads(fp.read_text())
                if old['checkpoints']!=frozen or old['frozen_settings_sha256']!=freeze_sha:raise ValueError('Frozen checkpoint list differs')
            else:write_json(fp,frozen_record)
            write_json(tr/'status.json',dict(state='completed',completed=30,planned=30,stage=stage))
            prior=next((r for r in stage_archives if r['kind']=='training'),None)
            archives.append(prior or pack(tr,sid,'training'));status('evaluating')
            for month in f['evaluation_months']:
                required=[HERE/'prepared'/cohort/(name+'.npz')for name in [f'evaluation_{month}',f'evaluation_groups_{month}']]
                while not all(x.exists()for x in required):
                    current=f'{sid}/awaiting_evaluation_upload/{month}';status('awaiting_evaluation_upload');check_budget();time.sleep(2)
                check_budget();current=f'{sid}/features/{month}';status('evaluating')
                data=read_split(cohort,f'evaluation_{month}');groups=read_split(cohort,f'evaluation_groups_{month}')
                if not np.array_equal(data['id'],groups['id']):raise ValueError('Evaluation group IDs differ')
                # Row-independent statistics; same 16 features, no model or data alteration.
                features=None  # M0 is evaluated on local CPU after verified training recovery.
                for seed in plan['seeds']:
                    for kind in ['M1','M2','M3','M4','M5']:
                        check_budget();name=f'{kind}_s{seed}_n{budget}';current=f'{sid}/{month}/{name}';status('evaluating');cp=checkpoints[kind,seed]
                        if digest(cp)!=frozen[name]:raise ValueError('Checkpoint changed after freeze')
                        eval_one(kind,seed,budget,cohort,cp,ev/month/name,cfg,f,freeze_sha,data,groups,features,check_budget)
                        evdone.append(current);status('evaluating')
                del data,groups,features;gc.collect()
            write_json(ev/'status.json',dict(state='completed',completed=50,planned=50,local_m0_pending=10,stage=stage))
            archives.append(pack(ev,sid,'evaluation'));finished.append(sid);status('stage_completed')
        current=None;status('completed')
    except BaseException as e:
        write_json(BASE/'failure.json',dict(type=type(e).__name__,message=str(e),traceback=traceback.format_exc()))
        if stage:
            for kind in ['training','evaluation']:
                folder=BASE/stage['id']/kind
                if folder.exists() and not any(r['stage']==stage['id']and r['kind']==kind for r in archives):
                    write_json(folder/'status.json',dict(state='partial',stage=stage,reason=str(e)))
                    archives.append(pack(folder,stage['id'],kind))
        status('budget_stopped'if isinstance(e,TimeoutError)else'failed');raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--minutes',type=float,default=110);a=p.parse_args()
    if not 1<=a.minutes<=110:p.error('Session limit1..110 minutes')
    run(a.minutes)
