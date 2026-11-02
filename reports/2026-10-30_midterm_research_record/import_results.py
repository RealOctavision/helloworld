"""Verify and register this development campaign's recovered ZIP. Never trains."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import zipfile
from zoneinfo import ZoneInfo
import numpy as np
import torch
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
EXP=ROOT/'experiments/2026-10-30_midterm_restart'
sys.path.insert(0,str(EXP))
from data import digest,load_config,read_split,write_json
from training import hash_bytes,metrics


def safe_names(z):
    seen=set()
    for info in z.infolist():
        p=PurePosixPath(info.filename)
        if p.is_absolute() or '..' in p.parts or '\\' in info.filename or not p.parts:
            raise ValueError(f'Unsafe ZIP path: {info.filename}')
        if info.filename in seen or stat.S_ISLNK(info.external_attr >> 16):
            raise ValueError(f'Duplicate/symlink ZIP entry: {info.filename}')
        seen.add(info.filename)
    if sum(i.file_size for i in z.infolist()) > 4*1024**3:
        raise ValueError('Unexpected archive expansion >4GiB')


def import_archive(path, expected):
    path=Path(path).resolve()
    if not re.fullmatch('[0-9a-fA-F]{64}',expected): raise ValueError('Expected SHA256 must be a complete digest obtained from Colab')
    archive_sha=digest(path)
    if archive_sha != expected.lower(): raise ValueError('Remote/local archive SHA256 mismatch')
    base=EXP/'colab_recovered'/archive_sha[:16]
    base.mkdir(parents=True,exist_ok=True)
    saved=base/'original_results.zip'
    if saved.exists():
        if digest(saved)!=archive_sha: raise ValueError('Existing archive path has different bytes')
    elif path != saved:
        shutil.copy2(path,saved)
    extracted=base/'extracted'
    extracted.mkdir(exist_ok=True)
    with zipfile.ZipFile(saved) as z:
        safe_names(z)
        bad=z.testzip()
        if bad: raise ValueError(f'CRC failed: {bad}')
        z.extractall(extracted)
    hpath=extracted/'colab_development/file_hashes.json'
    hashes=json.loads(hpath.read_text())
    for name,h in hashes.items():
        p=extracted/name
        if not p.resolve().is_relative_to(extracted.resolve()) or digest(p)!=h:
            raise ValueError(f'Inner file checksum mismatch: {name}')
    files={str(p.relative_to(extracted)) for p in extracted.rglob('*') if p.is_file()}
    if files != set(hashes)|{'colab_development/file_hashes.json'}:
        raise ValueError('File manifest incomplete/contains unexpected files')
    cfg=load_config()
    if digest(extracted/'config.json') != digest(EXP/'config.json'):
        raise ValueError('Archive uses another protocol; register it as a separate campaign')
    for name in ['data.py','models.py','training.py','colab_development.py']:
        if digest(extracted/name) != digest(HERE/'snapshots'/name):
            raise ValueError(f'Execution code differs from captured approved snapshot: {name}')
    out=extracted/'colab_development'
    status=json.loads((out/'status.json').read_text())
    runtime=json.loads((out/'runtime.json').read_text())
    cohort=cfg['primary_cohort']; classes=cfg['cohorts'][cohort]['classes']; c=len(classes)
    val=read_split(cohort,'validation')
    datasets={s:read_split(cohort,f'development_seed{s}',cfg['development_budget']) for s in cfg['development_seeds']}
    records=[]; objects={}; selected_ckpts={}; initial=defaultdict(set)
    for p in sorted((out/'fits').glob('*/metrics.json')):
        raw=json.loads(p.read_text()); run_id=p.parent.name
        match=re.fullmatch(r'(M[0-5])_s(\d+)_c([\de.+-]+)_a([\de.+-]+)_t([\de.+-]+)',run_id)
        if not match: raise ValueError(f'Unexpected run identity {run_id}')
        kind,seed,choice,alpha,temp=match.groups(); seed=int(seed); choice=float(choice); alpha=float(alpha); temp=float(temp)
        if seed not in datasets: raise ValueError('Unexpected development seed')
        train=datasets[seed]
        if raw['model']!=kind or raw['train_ids_sha256']!=hash_bytes(train['id']) or raw['validation_ids_sha256']!=hash_bytes(val['id']):
            raise ValueError(f'Input identity mismatch: {run_id}')
        checkpoint=p.parent/('best.txt' if kind=='M0' else 'best.pt')
        if digest(checkpoint)!=raw['best_checkpoint_sha256']: raise ValueError(f'Best checkpoint corrupt: {run_id}')
        tree_count=None
        if kind!='M0':
            allowed=dict(seed=seed,cohort=cohort,classes=classes,budget=200,phase='development',lr=choice,alpha=alpha,temperature=temp,total_epochs=50,completed_epochs=50,
                         config_sha256=digest(EXP/'config.json'),train_input_sha256=hash_bytes(train['X']),train_labels_sha256=hash_bytes(train['y']))
            for key,v in allowed.items():
                if raw.get(key)!=v: raise ValueError(f'{run_id}: mismatch {key}')
            if not raw['device'].startswith('cuda') or raw['device_name']!=runtime['device']: raise ValueError('Mixed training device')
            for name,h in raw['source_hashes'].items():
                if h!=digest(extracted/name): raise ValueError('Recorded source hash differs')
            if digest(p.parent/'last.pt')!=raw['last_checkpoint_sha256']: raise ValueError('Last checkpoint corrupt')
            for ck,epoch in [('best.pt',raw['selected_epoch']),('last.pt',50)]:
                cp=torch.load(p.parent/ck,map_location='cpu',weights_only=True)
                if cp['epoch']!=epoch or not all(k in cp for k in ['optimizer','scheduler','rng','history','model','meta']): raise ValueError('Incomplete resumable checkpoint')
                for key in ['model','cohort','classes','seed','budget','phase','lr','alpha','temperature','config_sha256','initial_state_sha256']:
                    if cp['meta'][key]!=raw[key]: raise ValueError(f'Checkpoint meta mismatch {run_id}/{key}')
                del cp
            if len(raw['history'])!=50: raise ValueError('Epoch history incomplete')
            for i,h in enumerate(raw['history'],1):
                if h['epoch']!=i or h['updates']!=i*32 or not math.isfinite(h['train_loss']): raise ValueError('Epoch/update/loss contract mismatch')
            best=max(raw['history'],key=lambda h:(h['validation']['macro_f1'],-h['validation']['gt_cross_entropy'],-h['epoch']))
            if best['epoch']!=raw['selected_epoch']: raise ValueError('Best epoch not selected by agreed rule')
            if kind=='M2' and not raw['bn_statistics_unchanged']: raise ValueError('M2 BN statistics changed')
            if kind=='M1' and raw['bn_statistics_unchanged']: raise ValueError('M1 BN never changed')
            if kind in ['M3','M4','M5']: initial[seed].add(raw['initial_state_sha256'])
        else:
            if raw['settings']['seed']!=seed or raw['settings']['num_leaves']!=int(choice) or raw['settings']['num_threads']!=1: raise ValueError('M0 setting mismatch')
            if not 1<=raw['completed_iterations']<=500: raise ValueError('M0 round budget mismatch')
            if not (p.parent/'last.txt').exists(): raise ValueError('M0 last checkpoint missing')
            best=max(raw['history'],key=lambda h:(h['validation']['macro_f1'],-h['validation']['gt_cross_entropy'],-h['iteration']))
            if best['iteration']!=raw['selected_iteration']: raise ValueError('M0 checkpoint selection mismatch')
            tree_count=sum(l.startswith('Tree=') for l in checkpoint.read_text().splitlines())
        with np.load(p.parent/'validation_predictions.npz',allow_pickle=False) as f:
            if not np.array_equal(f['id'],val['id']) or not np.array_equal(f['y'],val['y']): raise ValueError('Prediction rows/labels misaligned')
            probabilities=f['probabilities']
            if probabilities.shape!=(len(val['y']),c) or not np.isfinite(probabilities).all() or not np.allclose(probabilities.sum(1),1,atol=2e-6): raise ValueError('Invalid prediction probabilities')
            calculated=metrics(val['y'],probabilities,c)
        for k in ['macro_f1','accuracy']:
            if not math.isclose(calculated[k],raw['validation'][k],rel_tol=0,abs_tol=1e-8): raise ValueError(f'Prediction-derived {k} differs')
        if calculated['confusion']!=raw['validation']['confusion']: raise ValueError('Confusion matrix differs')
        cm=np.array(calculated['confusion']); tp=np.diag(cm)
        prec=np.divide(tp,cm.sum(0),out=np.zeros(c),where=cm.sum(0)>0)
        rec=np.divide(tp,cm.sum(1),out=np.zeros(c),where=cm.sum(1)>0)
        record=dict(run_id=run_id,model=kind,seed=seed,phase='development',cohort=cohort,budget=200,lr=choice if kind!='M0' else None,num_leaves=int(choice) if kind=='M0' else None,
            alpha=alpha,temperature=temp,selected_step=raw.get('selected_epoch',raw.get('selected_iteration')),completed_steps=raw.get('completed_epochs',raw.get('completed_iterations')),
            parameters=raw.get('parameters'),tree_count=tree_count,validation=raw['validation'],per_class_precision=prec.tolist(),per_class_recall=rec.tolist(),classes=classes,
            elapsed_seconds=raw['elapsed_seconds'],teacher_prediction_seconds=raw.get('teacher_prediction_seconds'),checkpoint_bytes=checkpoint.stat().st_size,
            train_ids_sha256=raw['train_ids_sha256'],validation_ids_sha256=raw['validation_ids_sha256'],initial_state_sha256=raw.get('initial_state_sha256'),
            best_checkpoint_sha256=raw['best_checkpoint_sha256'],teacher_checkpoint_sha256=raw.get('teacher_checkpoint_sha256'),
            source_metrics=str(p.relative_to(ROOT)),metrics_sha256=digest(p),checkpoint=str(checkpoint.relative_to(ROOT)),
            metadata_provenance='M0 phase/cohort/budget inferred from campaign config and validated IDs; neural metadata explicit' if kind=='M0' else 'explicit metrics and checked against prepared data',
            history=raw['history'],terminal_trend={'last_five_f1': [h['validation']['macro_f1'] for h in raw['history'][-5:]],'best_at_final_step': raw.get('selected_epoch',raw.get('selected_iteration'))==raw.get('completed_epochs',raw.get('completed_iterations'))})
        records.append(record); objects[run_id]=raw
        if kind in ['M1','M2']: selected_ckpts[raw['best_checkpoint_sha256']]=raw
    if any(len(v)!=1 for v in initial.values()): raise ValueError('Student initializations differ within seed')
    for r in records:
        if r['model'] not in ['M4','M5']: continue
        teacher=selected_ckpts.get(r['teacher_checkpoint_sha256']); raw=objects[r['run_id']]
        if teacher is None or teacher['model']!=('M1' if r['model']=='M4' else 'M2'): raise ValueError('Unmatched teacher')
        for k in ['seed','cohort','classes','budget','phase','train_ids_sha256','train_input_sha256','train_labels_sha256']:
            if teacher[k]!=raw[k]: raise ValueError('Teacher/student contract mismatch')
    counts=dict(Counter(r['model'] for r in records))
    selection=None
    if status['state']=='completed':
        expected_counts={'M0':6,'M1':6,'M2':6,'M3':6,'M4':18,'M5':18}
        if counts!=expected_counts or len(records)!=60: raise ValueError('Completed campaign missing fits')
        selection=json.loads((out/'selection.json').read_text())
        for model in ['M0','M1','M2','M3']:
            groups=defaultdict(list)
            for r in records:
                if r['model']==model: groups[r['num_leaves'] if model=='M0' else r['lr']].append(r)
            expected_choices=cfg['m0']['num_leaves_candidates'] if model=='M0' else cfg['training']['lr_candidates'][model if model in ['M1','M2'] else 'student']
            if set(groups)!=set(expected_choices) or any({r['seed'] for r in rows}!=set(cfg['development_seeds']) for rows in groups.values()): raise ValueError('Candidate/seed coverage incomplete')
            best=min(groups,key=lambda x:(-np.mean([r['validation']['macro_f1'] for r in groups[x]]),np.mean([r['validation']['gt_cross_entropy'] for r in groups[x]]),x))
            if selection['selected'][model]!=best: raise ValueError('LR/leaves selection differs')
        groups=defaultdict(list)
        for r in records:
            if r['model'] in ['M4','M5']:
                if r['lr']!=selection['selected']['M3']: raise ValueError('KD student LR is not common')
                teacher=selected_ckpts[r['teacher_checkpoint_sha256']]
                if teacher['lr']!=selection['selected'][teacher['model']]: raise ValueError('KD did not reuse chosen teacher')
                groups[r['alpha'],r['temperature']].append(r)
        if set(groups)!={(a,t) for a in cfg['kd']['alpha_candidates'] for t in cfg['kd']['temperature_candidates']}: raise ValueError('KD grid incomplete')
        if any({(r['model'],r['seed']) for r in rows}!={(m,s) for m in ['M4','M5'] for s in cfg['development_seeds']} for rows in groups.values()): raise ValueError('KD four-way coverage missing')
        best=min(groups,key=lambda x:(-np.mean([r['validation']['macro_f1'] for r in groups[x]]),np.mean([r['validation']['gt_cross_entropy'] for r in groups[x]]),*x))
        if best!=(selection['kd']['alpha'],selection['kd']['temperature']): raise ValueError('Joint KD selection differs')
        if not math.isclose(selection['kd']['mean_macro_f1'],float(np.mean([r['validation']['macro_f1'] for r in groups[best]])),abs_tol=1e-12): raise ValueError('Joint score differs')
    partial=[str(p.relative_to(ROOT)) for p in (out/'fits').glob('*/last.pt') if not (p.parent/'metrics.json').exists()]
    report=dict(imported_at=datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),status='verified',archive=str(saved.relative_to(ROOT)),archive_sha256=archive_sha,
        archive_bytes=saved.stat().st_size,verified_files=len(hashes),config_sha256=digest(EXP/'config.json'),runtime=runtime,campaign_status=status,counts=counts,
        records=records,selection=selection,partial_checkpoints=partial,scope='Development only. No April/May performance evaluated.',
        checks=['whole ZIP remote/local SHA256','safe unique paths and CRC','all inner file hashes','input/label/validation identities','model/code/config matching','completed epoch and update budget','best/last resumable checkpoint metadata','prediction-derived F1/accuracy/confusion','paired teacher and student initialization','complete candidate coverage and joint selection when completed'],
        missing_measurements=['per-run independent peak GPU VRAM','per-run exact wall-clock start/end','batch-level timing','full pip freeze/GPU driver unless separately recovered','final CPU benchmark','April/May predictions'])
    write_json(base/'verified_results.json',report)
    ledger_path=HERE/'result_registry.json'
    registry=json.loads(ledger_path.read_text()) if ledger_path.exists() else {'campaigns':[]}
    entry=dict(archive_sha256=archive_sha,verification=str((base/'verified_results.json').relative_to(ROOT)),campaign_started_utc=runtime['started_utc'],status=status['state'],completed=len(records),imported_at=report['imported_at'])
    registry['campaigns']=[e for e in registry['campaigns'] if e['archive_sha256']!=archive_sha]+[entry]
    write_json(ledger_path,registry)
    print(json.dumps(dict(verified=True,state=status['state'],completed=len(records),counts=counts,path=str(base/'verified_results.json')),ensure_ascii=False,indent=2))
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--archive',required=True); ap.add_argument('--expected-sha256',required=True)
    args=ap.parse_args(); import_archive(args.archive,args.expected_sha256)
