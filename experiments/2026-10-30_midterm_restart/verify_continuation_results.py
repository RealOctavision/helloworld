"""Verify stage-specific continuation archives with the established main checks. No fitting."""
import argparse
from collections import Counter,defaultdict
import json
from pathlib import Path,PurePosixPath
import shutil
import stat
import zipfile
import numpy as np
import torch
from data import HERE,ROOT,digest,read_split,write_json
from training import hash_bytes,metrics,selection_key
from colab_main import compact_metrics
from colab_continuation import settings

STAGE=None
def stage_settings():
    cfg,f,plan=settings()
    stage=next(s for s in plan['stages'] if s['id']==STAGE)
    f=dict(f,cohort=stage['cohort'],budget=stage['budget'])
    return cfg,f


def recover(path,expected,kind):
    path=Path(path).resolve()
    if digest(path)!=expected:raise ValueError('Archive remote/local SHA mismatch')
    base=HERE/'continuation_recovered'/STAGE/f'{kind}_{expected[:16]}';base.mkdir(parents=True,exist_ok=True)
    saved=base/'original_results.zip'
    if saved.exists():
        if digest(saved)!=expected:raise ValueError('Saved ZIP differs')
    else:shutil.copy2(path,saved)
    out=base/'extracted';out.mkdir(exist_ok=True)
    with zipfile.ZipFile(saved) as z:
        seen=set()
        if sum(i.file_size for i in z.infolist())>4*1024**3:raise ValueError('Oversize ZIP')
        for i in z.infolist():
            p=PurePosixPath(i.filename)
            if p.is_absolute() or '..'in p.parts or '\\'in i.filename or i.filename in seen or stat.S_ISLNK(i.external_attr>>16):raise ValueError('Unsafe/duplicate ZIP path')
            seen.add(i.filename)
        if z.testzip() is not None:raise ValueError('ZIP CRC failure')
        z.extractall(out)
    folder=f'continuation/{STAGE}/{kind}'
    hashes=json.loads((out/folder/'file_hashes.json').read_text())
    if {str(p.relative_to(out))for p in out.rglob('*')if p.is_file()} != set(hashes)|{folder+'/file_hashes.json'}:raise ValueError('Incomplete file manifest')
    for name,h in hashes.items():
        p=out/name
        if not p.resolve().is_relative_to(out.resolve()) or digest(p)!=h:raise ValueError('Inner checksum differs')
    uploaded=json.loads((HERE/'continuation_split_transfer.json').read_text())['train']['files']
    for name in ['config.json','main_frozen.json','continuation_frozen.json','data.py','models.py','training.py','colab_main.py','colab_continuation.py']:
        if digest(out/name)!=uploaded[str((HERE/name).relative_to(ROOT))]:raise ValueError('Uploaded code/config mismatch')
    return base,out,len(hashes)

def verify_training(path,expected):
    cfg,f=stage_settings();budget=f['budget'];C=len(cfg['cohorts'][f['cohort']]['classes']);base,out,files=recover(path,expected,'training')
    top=out/'continuation'/STAGE/'training';status=json.loads((top/'status.json').read_text())
    if status['state']!='completed':raise ValueError('Training archive is partial; raw preserved, do not label complete')
    frozen=json.loads((top/'frozen_checkpoints.json').read_text());freeze_sha=digest(HERE/'continuation_frozen.json')
    if frozen['frozen_settings_sha256']!=freeze_sha:raise ValueError('Frozen selection differs')
    val=read_split(f['cohort'],'validation');trains={s:read_split(f['cohort'],f'main_seed{s}',budget) for s in f['seeds']}
    records=[];initial=defaultdict(set)
    for seed in f['seeds']:
        train=trains[seed]
        for kind in ['M0','M1','M2','M3','M4','M5']:
            name=f'{kind}_s{seed}_n{budget}';p=top/'fits'/name
            r=json.loads((p/'metrics.json').read_text());c=json.loads((p/'run_context.json').read_text())
            choice=f['selected'].get(kind,f['selected']['M3']);alpha=.5 if kind in ['M4','M5'] else 0.
            expected_context=dict(stage=STAGE,model=kind,seed=seed,budget=budget,phase='main',cohort=f['cohort'],classes=cfg['cohorts'][f['cohort']]['classes'],
                frozen_settings_sha256=freeze_sha,choice=choice,alpha=alpha,temperature=1,
                train_ids_sha256=hash_bytes(train['id']),train_input_sha256=hash_bytes(train['X']),
                train_labels_sha256=hash_bytes(train['y']),validation_ids_sha256=hash_bytes(val['id']))
            if c!=expected_context:raise ValueError('Run context differs: '+name)
            cp=p/('best.txt' if kind=='M0' else 'best.pt');cp_sha=digest(cp)
            if cp_sha!=frozen['checkpoints'][name] or cp_sha!=r['best_checkpoint_sha256']:raise ValueError('Checkpoint digest differs')
            if r['model']!=kind or r['train_ids_sha256']!=c['train_ids_sha256'] or r['validation_ids_sha256']!=c['validation_ids_sha256']:raise ValueError('Run identities differ')
            if kind!='M0':
                for k,v in dict(seed=seed,budget=budget,phase='main',cohort=f['cohort'],lr=choice,alpha=alpha,temperature=1,total_epochs=50,completed_epochs=50,parameters=686613+449*C if kind in ['M1','M2'] else 18880+65*C).items():
                    if r.get(k)!=v:raise ValueError(f'{name} metadata {k}')
                if not r['device'].startswith('cuda'):raise ValueError('Neural fit was not CUDA')
                if len(r['history'])!=50 or any(h['epoch']!=i or h['updates']!=int(np.ceil(C*budget/128))*i or not np.isfinite(h['train_loss']) for i,h in enumerate(r['history'],1)):raise ValueError('Epoch budget differs')
                best=max(r['history'],key=lambda h:selection_key(h['validation'],h['epoch']))
                if best['epoch']!=r['selected_epoch']:raise ValueError('Selection rule differs')
                for filename,epoch in [('best.pt',r['selected_epoch']),('last.pt',50)]:
                    q=torch.load(p/filename,weights_only=True,map_location='cpu')
                    if q['epoch']!=epoch or not all(k in q for k in ['optimizer','scheduler','rng','history','meta','model']):raise ValueError('Missing resumable state')
                    for key in ['model','seed','phase','budget','cohort','classes','lr','alpha','temperature','config_sha256','initial_state_sha256','source_hashes']:
                        if q['meta'][key]!=r[key]:raise ValueError('Checkpoint metadata differs')
                    if not all(torch.isfinite(x).all() for x in q['model'].values() if x.is_floating_point()):raise ValueError('Nonfinite model tensors')
                    del q
                if digest(p/'last.pt')!=r['last_checkpoint_sha256']:raise ValueError('Last checkpoint corrupt')
                if kind=='M2' and not r['bn_statistics_unchanged']:raise ValueError('M2 BN changed')
                if kind=='M1' and r['bn_statistics_unchanged']:raise ValueError('M1 BN did not update')
                if kind in ['M3','M4','M5']:initial[seed].add(r['initial_state_sha256'])
                if r['config_sha256']!=f['base_config_sha256']:raise ValueError('Base config differs')
                for n,h in r['source_hashes'].items():
                    if digest(out/n)!=h:raise ValueError('Source metadata differs')
            else:
                if r['settings']['seed']!=seed or r['settings']['num_leaves']!=31 or r['settings']['num_threads']!=1:raise ValueError('Tree settings differ')
                if not 1<=r['completed_iterations']<=500 or not (p/'last.txt').exists():raise ValueError('Tree round/state missing')
                best=max(r['history'],key=lambda h:selection_key(h['validation'],h['iteration']))
                if best['iteration']!=r['selected_iteration']:raise ValueError('Tree selection differs')
            with np.load(p/'validation_predictions.npz',allow_pickle=False) as z:
                if not np.array_equal(z['id'],val['id']) or not np.array_equal(z['y'],val['y']):raise ValueError('Validation order differs')
                prob=z['probabilities']
                if not np.isfinite(prob).all() or prob.shape!=(len(val['y']),C) or not np.allclose(prob.sum(1),1,atol=2e-6):raise ValueError('Invalid validation probabilities')
                m=metrics(z['y'],prob,C)
            if m['confusion']!=r['validation']['confusion'] or abs(m['macro_f1']-r['validation']['macro_f1'])>1e-10:raise ValueError('Validation metrics differ')
            resources=json.loads((p/'resources.json').read_text())
            records.append(dict(run=name,model=kind,seed=seed,metrics_path=str((p/'metrics.json').relative_to(ROOT)),
                checkpoint=str(cp.relative_to(ROOT)),checkpoint_sha256=cp_sha,context=c,resources=resources,validation=r['validation'],
                selected_step=r.get('selected_epoch',r.get('selected_iteration')),completed_steps=r.get('completed_epochs',r.get('completed_iterations')),
                parameters=r.get('parameters'),initial_state_sha256=r.get('initial_state_sha256'),teacher_checkpoint_sha256=r.get('teacher_checkpoint_sha256')))
    if set(frozen['checkpoints'])!={r['run'] for r in records} or any(len(h)!=1 for h in initial.values()):raise ValueError('Coverage or initialization differs')
    lookup={(r['model'],r['seed']):r for r in records}
    for r in records:
        if r['model'] in ['M4','M5']:
            t=lookup['M1' if r['model']=='M4' else 'M2',r['seed']]
            if r['teacher_checkpoint_sha256']!=t['checkpoint_sha256']:raise ValueError('Matched teacher differs')
    report=dict(verified=True,archive_sha256=expected,archive=str((base/'original_results.zip').relative_to(ROOT)),
                extracted=str(out.relative_to(ROOT)),verified_files=files,records=records,completed=30,
                frozen_settings_sha256=freeze_sha,runtime=json.loads((top/'runtime.json').read_text()),status=status)
    write_json(base/'verified_training.json',report)
    write_json(HERE/'continuation_recovered'/STAGE/'training_registry.json',dict(verification=str((base/'verified_training.json').relative_to(ROOT))))
    print(json.dumps(dict(verified=True,kind='training',completed=30,root=str(out)),ensure_ascii=False))
    return report

def verify_evaluation(path,expected):
    cfg,f=stage_settings();budget=f['budget'];C=len(cfg['cohorts'][f['cohort']]['classes']);base,out,files=recover(path,expected,'evaluation')
    reg=json.loads((HERE/'continuation_recovered'/STAGE/'training_registry.json').read_text());training=json.loads((ROOT/reg['verification']).read_text())
    top=out/'continuation'/STAGE/'evaluation';status=json.loads((top/'status.json').read_text())
    if status['state']!='completed':raise ValueError('Evaluation partial; raw preserved')
    check={r['run']:r['checkpoint_sha256'] for r in training['records']};records=[]
    for month in f['evaluation_months']:
        d=read_split(f['cohort'],f'evaluation_{month}');g=read_split(f['cohort'],f'evaluation_groups_{month}')
        if not np.array_equal(d['id'],g['id']):raise ValueError('Grouping order differs')
        identity=dict(evaluation_ids_sha256=hash_bytes(d['id']),evaluation_input_sha256=hash_bytes(d['X']),evaluation_labels_sha256=hash_bytes(d['y']))
        for seed in f['seeds']:
            overlap=g[f'seed{seed}_n{budget}_train_overlap'];unseen=g['common_unseen']
            masks=dict(all=np.ones(len(overlap),bool),train_overlap=overlap,train_nonoverlap=~overlap,common_unseen=unseen)
            for kind in ['M1','M2','M3','M4','M5']:
                name=f'{kind}_s{seed}_n{budget}';p=top/month/name;r=json.loads((p/'metrics.json').read_text())
                if r['checkpoint_sha256']!=check[name] or r['frozen_settings_sha256']!=training['frozen_settings_sha256']:raise ValueError('Evaluation checkpoint/protocol differs')
                if any(r[k]!=v for k,v in dict(model=kind,seed=seed,month=month,budget=budget,phase='evaluation',cohort=f['cohort'],classes=cfg['cohorts'][f['cohort']]['classes'],**identity).items()):raise ValueError('Evaluation identity differs')
                if digest(p/'predictions.npz')!=r['prediction_sha256']:raise ValueError('Prediction checksum differs')
                with np.load(p/'predictions.npz',allow_pickle=False) as z:
                    if not np.array_equal(z['id'],d['id']) or not np.array_equal(z['y'],d['y']):raise ValueError('Prediction row identities differ')
                    pred=z['predicted_label'];lp=z['true_log_probability'];conf=z['maximum_probability']
                    if not (pred.shape==lp.shape==conf.shape==d['y'].shape) or not np.isfinite(lp).all() or not np.isfinite(conf).all() or np.any(pred>=C) or np.any(lp>1e-6) or np.any(conf<0) or np.any(conf>1):raise ValueError('Invalid compact predictions')
                    for group,mask in masks.items():
                        m=compact_metrics(d['y'][mask],pred[mask],lp[mask],C);actual=r['groups'][group]
                        for key in ['n','support','confusion','classes_with_support']:
                            if m[key]!=actual[key]:raise ValueError('Group counts/confusion differ')
                        for key in ['macro_f1','accuracy','gt_cross_entropy','per_class_f1','per_class_precision','per_class_recall']:
                            if m['n']==0:
                                if m[key]!=actual[key]:raise ValueError('Empty group reporting differs')
                            elif not np.allclose(m[key],actual[key],atol=1e-10,rtol=0):raise ValueError('Group metric differs')
                records.append(dict(**r,metrics_path=str((p/'metrics.json').relative_to(ROOT)),prediction_path=str((p/'predictions.npz').relative_to(ROOT))))
    report=dict(verified=True,completed=50,archive_sha256=expected,archive=str((base/'original_results.zip').relative_to(ROOT)),
                verified_files=files,training_verification=reg['verification'],records=records,scope=f'{STAGE}: five main seeds; CUDA neural evaluation50; local M0 evaluation10 pending; April primary and May temporal; no test-set tuning')
    write_json(base/'verified_evaluation.json',report)
    write_json(HERE/'continuation_recovered'/STAGE/'evaluation_registry.json',dict(verification=str((base/'verified_evaluation.json').relative_to(ROOT))))
    print(json.dumps(dict(verified=True,kind='evaluation',completed=50,path=str(base/'verified_evaluation.json')),ensure_ascii=False))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['training','evaluation']);p.add_argument('--stage',required=True,choices=['mixed_n50','mixed_n100','mixed_n1000','nongoogle_n200','googleonly_n200']);p.add_argument('--archive',required=True);p.add_argument('--sha256',required=True);a=p.parse_args();STAGE=a.stage
    (verify_training if a.kind=='training' else verify_evaluation)(a.archive,a.sha256)
