"""CPU1 evaluation of verified continuation M0 checkpoints; never fits a model."""
import argparse,gc,importlib.metadata,json,platform,time
from pathlib import Path
import numpy as np
import lightgbm as lgb
from data import HERE,ROOT,digest,read_split,save_npz,write_json
from models import statistics
from training import hash_bytes
from colab_main import compact_metrics
from colab_continuation import settings

def run(stage_id):
    cfg,f,plan=settings();stage=next(s for s in plan['stages']if s['id']==stage_id)
    cohort,budget=stage['cohort'],stage['budget'];C=len(cfg['cohorts'][cohort]['classes'])
    base=HERE/'continuation_recovered'/stage_id
    reg=json.loads((base/'training_registry.json').read_text());training=json.loads((ROOT/reg['verification']).read_text())
    if not training['verified'] or training['completed']!=30:raise ValueError('Verified training required')
    if importlib.metadata.version('lightgbm')!='4.6.0':raise ValueError('Pinned LightGBM version required')
    preflight=json.loads((HERE/'continuation_preflight.json').read_text())
    if not preflight.get('passed'):raise ValueError('M0 preflight required')
    outroot=base/'local_m0_evaluation';outroot.mkdir(exist_ok=True)
    runtime=dict(python=platform.python_version(),platform=platform.platform(),lightgbm=importlib.metadata.version('lightgbm'),numpy=np.__version__,num_threads=1,
        script_sha256=digest(Path(__file__)),frozen_settings_sha256=digest(HERE/'continuation_frozen.json'),preflight_sha256=digest(HERE/'continuation_preflight.json'),
        note='Same existing tree and exact cached16 PPI statistics; CPU1 evaluation only. Cross-platform probability last bits may differ; full bitwise equivalence not claimed.')
    write_json(outroot/'runtime.json',runtime)
    check={r['run']:r for r in training['records']};records=[]
    for month in f['evaluation_months']:
        data=read_split(cohort,f'evaluation_{month}');groups=read_split(cohort,f'evaluation_groups_{month}')
        if not np.array_equal(data['id'],groups['id']):raise ValueError('Group ID mismatch')
        t=time.perf_counter();features=statistics(data['X'])[0];feature_seconds=time.perf_counter()-t
        for seed in plan['seeds']:
            name=f'M0_s{seed}_n{budget}';cp=ROOT/check[name]['checkpoint'];cp_sha=digest(cp)
            if cp_sha!=check[name]['checkpoint_sha256']:raise ValueError('Checkpoint changed')
            out=outroot/month/name;out.mkdir(parents=True,exist_ok=True)
            ident=dict(model='M0',seed=seed,budget=budget,cohort=cohort,classes=cfg['cohorts'][cohort]['classes'],month=month,phase='evaluation',
                checkpoint_sha256=cp_sha,frozen_settings_sha256=runtime['frozen_settings_sha256'],evaluation_ids_sha256=hash_bytes(data['id']),
                evaluation_input_sha256=hash_bytes(data['X']),evaluation_labels_sha256=hash_bytes(data['y']))
            predpath=out/'predictions.npz';metricpath=out/'metrics.json'
            if metricpath.exists():
                r=json.loads(metricpath.read_text())
                if any(r[k]!=v for k,v in ident.items()) or digest(predpath)!=r['prediction_sha256']:raise ValueError('Resume mismatch')
            else:
                t=time.perf_counter();model=lgb.Booster(model_file=str(cp));n=len(data['y'])
                pred=np.empty(n,dtype='u1');lp=np.empty(n,dtype='f4');confidence=np.empty(n,dtype='f4')
                for off in range(0,n,f['evaluation']['batch_size']):
                    end=min(n,off+f['evaluation']['batch_size']);y=data['y'][off:end]
                    prob=model.predict(features[off:end],num_threads=1)
                    if not np.isfinite(prob).all() or not np.allclose(prob.sum(1),1,atol=2e-6):raise ValueError('Invalid tree probabilities')
                    pred[off:end]=prob.argmax(1);confidence[off:end]=prob.max(1);lp[off:end]=np.log(np.clip(prob[np.arange(len(y)),y],1e-30,1))
                save_npz(predpath,id=data['id'],y=data['y'].astype('u1'),predicted_label=pred,true_log_probability=lp,maximum_probability=confidence)
                overlap=groups[f'seed{seed}_n{budget}_train_overlap'];unseen=groups['common_unseen']
                if np.any(overlap&unseen):raise ValueError('Mask overlap')
                masks=dict(all=np.ones(n,bool),train_overlap=overlap,train_nonoverlap=~overlap,common_unseen=unseen)
                r=dict(**ident,prediction_sha256=digest(predpath),groups={k:compact_metrics(data['y'][m],pred[m],lp[m],C)for k,m in masks.items()},
                    device='local_cpu1',seconds=time.perf_counter()-t,num_threads=1,shared_feature_compute_seconds=feature_seconds,
                    prediction_storage=f['evaluation']['compact_prediction_storage'],runtime_sha256=digest(outroot/'runtime.json'))
                write_json(metricpath,r);del model
            with np.load(predpath,allow_pickle=False)as z:
                if not np.array_equal(z['id'],data['id']) or not np.array_equal(z['y'],data['y']):raise ValueError('Prediction identity mismatch')
                overlap=groups[f'seed{seed}_n{budget}_train_overlap']
                masks=dict(all=np.ones(len(overlap),bool),train_overlap=overlap,train_nonoverlap=~overlap,common_unseen=groups['common_unseen'])
                for group,mask in masks.items():
                    actual=compact_metrics(z['y'][mask],z['predicted_label'][mask],z['true_log_probability'][mask],C)
                    if actual!=r['groups'][group]:raise ValueError('Saved metrics mismatch')
            records.append(dict(**r,metrics_path=str(metricpath.relative_to(ROOT)),prediction_path=str(predpath.relative_to(ROOT))))
            print(json.dumps(dict(stage=stage_id,month=month,run=name,completed=len(records),planned=10)),flush=True)
        del data,groups,features;gc.collect()
    report=dict(verified=True,stage=stage_id,completed=10,training_verification=reg['verification'],records=records,runtime=runtime)
    write_json(outroot/'verified_evaluation.json',report)
    write_json(base/'local_m0_registry.json',dict(verification=str((outroot/'verified_evaluation.json').relative_to(ROOT))))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);a=p.parse_args();run(a.stage)
