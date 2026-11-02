"""Bounded, resumable development only. No April/May data or main fits."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import argparse
import fcntl
import importlib.metadata
import json
from pathlib import Path
import platform
import time
import traceback
import zipfile
import numpy as np
import torch
from data import HERE, digest, load_config, read_split, write_json
from training import fit_network, fit_m0

OUT = HERE / 'colab_development'
ARCHIVE = HERE / 'colab_development_results.zip'


def archive():
    paths = sorted(p for p in OUT.rglob('*') if p.is_file() and p.suffix != '.tmp')
    paths += [HERE / p for p in ['config.json','data.py','models.py','training.py','colab_development.py']]
    write_json(OUT/'file_hashes.json', {str(p.relative_to(HERE)): digest(p) for p in paths if p.name != 'file_hashes.json'})
    paths = [p for p in paths if p.name != 'file_hashes.json'] + [OUT/'file_hashes.json']
    temp = ARCHIVE.with_suffix('.tmp')
    with zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for p in paths:
            z.write(p, str(p.relative_to(HERE)))
    temp.replace(ARCHIVE)
    print('ARCHIVE', ARCHIVE, ARCHIVE.stat().st_size, digest(ARCHIVE), flush=True)


def select_candidate(candidates):
    """Mean across fixed two development seeds; lower CE then lower candidate."""
    return min(candidates, key=lambda r: (-r['mean_macro_f1'], r['mean_gt_ce'], r['candidate']))


def run(minutes):
    cfg = load_config()
    if not torch.cuda.is_available():
        raise RuntimeError('GPU is required; refusing CPU campaign')
    OUT.mkdir(exist_ok=True)
    lock = (OUT/'runner.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    start = time.monotonic()
    deadline = start + minutes*60
    cohort = cfg['primary_cohort']
    budget = cfg['development_budget']
    seeds = cfg['development_seeds']
    val = read_split(cohort, 'validation')
    train = {s: read_split(cohort, f'development_seed{s}', budget) for s in seeds}
    runtime = dict(pid=os.getpid(), started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        device=torch.cuda.get_device_name(0), python=platform.python_version(),
        packages={p: importlib.metadata.version(p) for p in ['torch','numpy','cesnet-models','lightgbm']},
        cuda=torch.version.cuda, memory_bytes=torch.cuda.get_device_properties(0).total_memory,
        time_limit_minutes=minutes, precision='FP32; TF32 disabled; batch128',
        source_config_sha256=digest(HERE/'config.json'), planned_development_fits=60,
        benchmark_fits=3, evaluation_months_accessed=False,
        note='Only development data. M0 is a single-thread CPU tree baseline, neural M1-M5 use CUDA.')
    write_json(OUT/'runtime.json', runtime)
    done = []

    def status(state, current=None):
        write_json(OUT/'status.json', dict(state=state,current=current,completed=len(done),
            planned=60,elapsed_seconds=time.monotonic()-start,completed_runs=done))

    def check_time():
        if time.monotonic() > deadline-20:
            raise TimeoutError('Session budget reached; recover archive/checkpoints before releasing GPU')

    def fit(kind, seed, candidate, *, teacher=None, alpha=0., temperature=1, benchmark=False):
        check_time()
        name = f'{kind}_s{seed}_c{candidate:g}_a{alpha:g}_t{temperature:g}'
        directory = OUT/('benchmark' if benchmark else 'fits')/name
        mp = directory/'metrics.json'
        status('benchmark' if benchmark else 'running', name)
        if mp.exists():
            m = json.loads(mp.read_text())
            ckpt = directory/('best.txt' if kind=='M0' else 'best.pt')
            if digest(ckpt) != m['best_checkpoint_sha256']:
                raise ValueError('Existing completed checkpoint hash mismatch')
        elif kind == 'M0':
            _, m = fit_m0(train[seed], val, cfg, directory, seed, num_leaves=int(candidate))
        else:
            last = directory/'last.pt'
            _, m = fit_network(kind, train[seed], val, cfg, directory, cohort, seed, budget,
                candidate, 2 if benchmark else cfg['training']['candidate_epochs'], device='cuda',
                teacher_checkpoint=teacher, alpha=alpha, temperature=temperature,
                phase='benchmark' if benchmark else 'development',
                warmup_epochs=1 if benchmark else None,
                time_limit=max(1,deadline-time.monotonic()-20), resume_from=last if last.exists() else None)
        if not benchmark:
            done.append(name)
            status('running',name)
            archive()
        return m, directory

    try:
        benchmarks = {}
        for kind in ['M1','M2','M3']:
            lrs = cfg['training']['lr_candidates'][kind if kind!='M3' else 'student']
            m, _ = fit(kind,seeds[0],lrs[1],benchmark=True)
            benchmarks[kind] = dict(epoch_seconds=float(np.mean([h['fitting_seconds']+h['validation_seconds'] for h in m['history']])), validation=m['validation'])
        # Neural grid = 6 runs per M1/M2 and 42 student runs (M3 six + KD36).
        estimate = 50*(6*benchmarks['M1']['epoch_seconds']+6*benchmarks['M2']['epoch_seconds']+42*benchmarks['M3']['epoch_seconds'])
        write_json(OUT/'benchmark.json',dict(models=benchmarks,estimated_neural_development_seconds=estimate,
            excludes='M0, checkpoint/archive I/O, teacher prediction and overhead; not final model performance'))
        print('BENCHMARK estimated neural development seconds',estimate,flush=True)
        selected, comparisons, checkpoints = {}, {}, {}
        for kind in ['M1','M2','M3','M0']:
            choices = cfg['m0']['num_leaves_candidates'] if kind=='M0' else cfg['training']['lr_candidates'][kind if kind in ['M1','M2'] else 'student']
            results=[]
            for candidate in choices:
                scores=[]
                for seed in seeds:
                    m, directory = fit(kind,seed,candidate)
                    scores.append(m['validation'])
                    checkpoints[kind,seed,candidate] = directory/('best.txt' if kind=='M0' else 'best.pt')
                results.append(dict(candidate=candidate,mean_macro_f1=float(np.mean([v['macro_f1'] for v in scores])),
                    mean_gt_ce=float(np.mean([v['gt_cross_entropy'] for v in scores]))))
            comparisons[kind]=results
            selected[kind]=select_candidate(results)['candidate']
            write_json(OUT/'selection_partial.json',dict(selected=selected,comparisons=comparisons,source='February development only; no main fits'))
        kd=[]
        for alpha in cfg['kd']['alpha_candidates']:
            for temperature in cfg['kd']['temperature_candidates']:
                scores=[]
                for kind,teacher_kind in [('M4','M1'),('M5','M2')]:
                    for seed in seeds:
                        m,_=fit(kind,seed,selected['M3'],teacher=checkpoints[teacher_kind,seed,selected[teacher_kind]],alpha=alpha,temperature=temperature)
                        scores.append(m['validation'])
                kd.append(dict(alpha=alpha,temperature=temperature,mean_macro_f1=float(np.mean([v['macro_f1'] for v in scores])),mean_gt_ce=float(np.mean([v['gt_cross_entropy'] for v in scores]))))
                write_json(OUT/'kd_grid.json',kd)
        chosen=min(kd,key=lambda r:(-r['mean_macro_f1'],r['mean_gt_ce'],r['alpha'],r['temperature']))
        write_json(OUT/'selection.json',dict(selected=selected,kd=chosen,lr_comparisons=comparisons,kd_grid=kd,
            epochs=50,epochs_frozen=False,requires='Review learning curves before main-stage freeze',
            seeds=seeds,cohort=cohort,budget=budget,evaluation_months_accessed=False))
        status('completed')
    except BaseException as e:
        status('budget_stopped' if isinstance(e,TimeoutError) else 'failed')
        write_json(OUT/'failure.json',dict(type=type(e).__name__,message=str(e),traceback=traceback.format_exc()))
        raise
    finally:
        archive()

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--minutes',type=float,default=55)
    args=p.parse_args()
    if not 1 <= args.minutes <= 60:
        p.error('Budget must be 1..60 minutes')
    run(args.minutes)
