"""CE-only 64/128/128 student, paired with the published M3 samples.

The midterm files are read-only dependencies. Only February is scored here.
"""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')

import argparse
import fcntl
import json
import math
from pathlib import Path
import platform
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / '2026-10-30_midterm_restart'
sys.path.insert(0, str(BASE))

import numpy as np
import torch
from torch import nn
import data
import models
import training

COHORT = 'google_included20'
KIND = 'M3_wide'
CHANNELS = [64, 128, 128]
BASE_HASHES = {
    'config.json': 'f1b4de11292ae7bbd0d4a76f47deedf6f63798e8edc509e55a2a82f9ed8409fa',
    'main_frozen.json': 'e8f529a9d1e080c3a5c1faba10b20b439ab6221206173258aa51e74dd4197054',
    'data.py': '9bfcaced8696fe9e4dd348e493a6a7931038753517e5620beb203731ac4734a4',
    'models.py': '8e01ad21e877e7c9e54b69eb73f2283ebe1367a7a6392853d0583216dfbd16b1',
    'training.py': 'e25568e097d4b1d04465123554e3f54c18e971aa6030b51b04bdf336438fc955',
}


class WideStudent(models.Student):
    def __init__(self, classes):
        # Inherit the exact scaling, masking, ReLU and pooling implementation.
        nn.Module.__init__(self)
        self.drop_channel = None
        self.blocks = nn.ModuleList([
            nn.Conv1d(3, 64, 3, padding=1),
            nn.Conv1d(64, 128, 3, padding=1),
            nn.Conv1d(128, 128, 3, padding=1),
        ])
        self.head = nn.Linear(128, classes)


def make_wide_model(kind, classes, seed, cfg):
    if kind != KIND or classes != 20:
        raise ValueError('This experiment supports only M3_wide / 20 classes')
    torch.manual_seed(seed + 10000)
    model = WideStudent(classes)
    torch.manual_seed(seed + 20000)
    model.head.reset_parameters()
    if sum(p.numel() for p in model.parameters()) != 77204:
        raise ValueError('Unexpected wide architecture')
    return model


def settings():
    for name, expected in BASE_HASHES.items():
        if data.digest(BASE / name) != expected:
            raise ValueError(f'Midterm dependency changed: {name}')
    cfg = data.load_config()
    frozen = json.loads((BASE / 'main_frozen.json').read_text())
    cfg['training']['epochs_frozen'] = True
    cfg['student']['channels'] = CHANNELS
    cfg['student']['params_20classes'] = 77204
    return cfg, frozen


def fit_wide(*args, **kwargs):
    # Local, scoped factory substitution keeps the frozen training file intact.
    original = training.make_model
    training.make_model = make_wide_model
    try:
        return training.fit_network(KIND, *args, **kwargs)
    finally:
        training.make_model = original


def split_hashes(train, val):
    return {
        f'{prefix}_{field}_sha256': training.hash_bytes(split[key])
        for prefix, split in [('train', train), ('validation', val)]
        for field, key in [('ids', 'id'), ('input', 'X'), ('labels', 'y')]
    }


def baseline(seed, budget, hashes):
    if budget == 200:
        pattern = f'main_recovered/training_*/extracted/main_training/fits/M3_s{seed}_n200/metrics.json'
    else:
        pattern = f'continuation_recovered/mixed_n1000/training_*/extracted/continuation/mixed_n1000/training/fits/M3_s{seed}_n1000/metrics.json'
    paths = list(BASE.glob(pattern))
    if not paths:
        return None
    if len(paths) != 1:
        raise ValueError('Multiple baseline records; resolve before comparing')
    old = json.loads(paths[0].read_text())
    expected = dict(model='M3', cohort=COHORT, seed=seed, budget=budget,
                    lr=0.003, total_epochs=50, alpha=0.0, parameters=20180,
                    config_sha256=BASE_HASHES['config.json'])
    expected.update({k: v for k, v in hashes.items() if k in [
        'train_ids_sha256', 'train_input_sha256', 'train_labels_sha256',
        'validation_ids_sha256']})
    if any(old.get(k) != v for k, v in expected.items()):
        raise ValueError(f'Baseline/data mismatch: {paths[0]}')
    return dict(path=str(paths[0].relative_to(BASE)), validation=old['validation'],
                torch_version=old['torch_version'], cuda_version=old['cuda_version'],
                device_name=old['device_name'])


def bind_context(folder, context):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'run_context.json'
    if path.exists():
        if json.loads(path.read_text()) != context:
            raise ValueError(f'Run settings/data/environment changed: {folder}; use a new output directory')
    else:
        if any(folder.iterdir()):
            raise ValueError(f'Unidentified existing files: {folder}')
        data.write_json(path, context)


def completed_result(folder):
    path = folder / 'metrics.json'
    if not path.exists():
        return None
    result = json.loads(path.read_text())
    for which in ['best', 'last']:
        if data.digest(folder / f'{which}.pt') != result[f'{which}_checkpoint_sha256']:
            raise ValueError(f'Corrupt {which} checkpoint: {folder}')
    return result


def train_score(model, train, device):
    logits = training.logits_for(model, train['X'], torch.device(device))
    return training.metrics(train['y'], logits.softmax(1).numpy(), 20)


def summarize(rows):
    groups = {}
    for budget in sorted({r['budget'] for r in rows}):
        selected = [r for r in rows if r['budget'] == budget]
        values = [r['validation']['macro_f1'] for r in selected]
        deltas = [r['delta_validation_macro_f1_pp'] for r in selected
                  if r['delta_validation_macro_f1_pp'] is not None]
        groups[str(budget)] = dict(
            seeds=[r['seed'] for r in selected],
            validation_macro_f1_mean=float(np.mean(values)),
            validation_macro_f1_sample_std=float(np.std(values, ddof=1)) if len(values) > 1 else None,
            paired_seed_count=len(deltas),
            paired_delta_macro_f1_pp_mean=float(np.mean(deltas)) if deltas else None)
    return groups


def run(args):
    cfg, frozen = settings()
    if args.dry_run:
        print(json.dumps(dict(model=KIND, channels=CHANNELS, parameters=77204,
            budgets=args.budgets, seeds=args.seeds, fits=len(args.budgets)*len(args.seeds),
            lr=frozen['selected']['M3'], epochs=frozen['epochs'],
            training=cfg['training'], evaluation='February validation only'), indent=2))
        return
    if args.device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; choose a GPU runtime (or explicitly --device cpu)')
    output = args.output.resolve()
    if output == BASE or BASE in output.parents:
        raise ValueError('Output must be outside the preserved midterm directory')
    output.mkdir(parents=True, exist_ok=True)
    lock = (output / 'runner.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _run_locked(args, cfg, frozen, output)
    finally:
        lock.close()


def _run_locked(args, cfg, frozen, output):
    deadline = time.monotonic() + args.minutes * 60
    val = data.read_split(COHORT, 'validation')
    environment = dict(python=platform.python_version(), torch=str(torch.__version__),
                       numpy=np.__version__, cuda=torch.version.cuda, device=args.device,
                       device_name=torch.cuda.get_device_name(0) if args.device == 'cuda' else platform.machine())
    source_hashes = dict(BASE_HASHES, runner=data.digest(Path(__file__)))
    rows = []
    current = None

    def status(state, error=None):
        data.write_json(output / 'summary.json', dict(state=state, current=current,
            planned_fits=len(args.budgets)*len(args.seeds), completed_fits=len(rows),
            environment=environment, runs=rows, by_budget=summarize(rows), error=error,
            scores_are_fractions=True, delta_unit='percentage points',
            April_May_evaluated=False))

    try:
        status('running')
        for budget in args.budgets:
            for seed in args.seeds:
                current = f'{KIND}_s{seed}_n{budget}'
                folder = output / current
                train = data.read_split(COHORT, f'main_seed{seed}', budget)
                hashes = split_hashes(train, val)
                old = baseline(seed, budget, hashes)
                context = dict(model=KIND, channels=CHANNELS, parameters=77204,
                    cohort=COHORT, seed=seed, budget=budget, lr=frozen['selected']['M3'],
                    epochs=frozen['epochs'], effective_config=cfg, source_hashes=source_hashes,
                    environment=environment, baseline=old, **hashes)
                bind_context(folder, context)
                result = completed_result(folder)
                if result is None:
                    if time.monotonic() >= deadline:
                        raise TimeoutError('Session budget reached; rerun the same command to resume')
                    model, result = fit_wide(train, val, cfg, folder, COHORT, seed, budget,
                        frozen['selected']['M3'], frozen['epochs'], device=args.device,
                        phase='main', alpha=0.0, teacher_checkpoint=None,
                        time_limit=max(0.001, deadline-time.monotonic()),
                        resume_from=folder/'last.pt' if (folder/'last.pt').exists() else None)
                else:
                    model = make_wide_model(KIND, 20, seed, cfg).to(args.device)
                    training.load_checkpoint(folder / 'best.pt', model)
                # The shared loop records per-epoch train loss. Score the selected
                # checkpoint once on training data to diagnose the generalization gap.
                diagnostic = folder / 'diagnostics.json'
                if diagnostic.exists():
                    detail = json.loads(diagnostic.read_text())
                    if detail['best_checkpoint_sha256'] != result['best_checkpoint_sha256']:
                        raise ValueError('Diagnostics belong to a different checkpoint')
                else:
                    detail = dict(best_checkpoint_sha256=result['best_checkpoint_sha256'],
                                  train_at_selected_checkpoint=train_score(model, train, args.device))
                    data.write_json(diagnostic, detail)
                row = dict(model=KIND, channels=CHANNELS, parameters=77204, seed=seed, budget=budget,
                    selected_epoch=result['selected_epoch'], validation=result['validation'],
                    train=detail['train_at_selected_checkpoint'],
                    updates=result['history'][-1]['updates'],
                    baseline_validation=None if old is None else old['validation'],
                    delta_validation_macro_f1_pp=None if old is None else
                        100*(result['validation']['macro_f1']-old['validation']['macro_f1']),
                    baseline_environment_matches=None if old is None else
                        (old['torch_version'] == environment['torch'] and
                         old['cuda_version'] == environment['cuda'] and
                         old['device_name'] == environment['device_name']))
                rows.append(row)
                print(json.dumps({k: row[k] for k in ['seed', 'budget', 'delta_validation_macro_f1_pp',
                    'baseline_environment_matches']}), flush=True)
                del model, train
                if args.device == 'cuda':
                    torch.cuda.empty_cache()
                status('running')
        current = None
        status('completed')
    except BaseException as exc:
        status('budget_stopped' if isinstance(exc, TimeoutError) else 'failed', str(exc))
        raise


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--budgets', type=int, nargs='+', choices=[200, 1000], default=[200, 1000])
    p.add_argument('--seeds', type=int, nargs='+', choices=range(201, 206), default=[201, 202])
    p.add_argument('--device', choices=['cuda', 'cpu'], default='cuda')
    p.add_argument('--minutes', type=float, default=45)
    p.add_argument('--output', type=Path, default=HERE/'runs')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args(argv)
    if not math.isfinite(args.minutes) or args.minutes <= 0:
        p.error('--minutes must be finite and positive')
    if len(set(args.budgets)) != len(args.budgets) or len(set(args.seeds)) != len(args.seeds):
        p.error('Duplicate budgets or seeds')
    return args


if __name__ == '__main__':
    run(parse_args())
