"""Shared fitting/checkpoint/evaluation primitives. No campaign on import."""
import math
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
from pathlib import Path
import time

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from data import HERE, digest, write_json, save_npz
from models import make_model, state_digest, statistics, kd_loss


def metrics(y, probabilities, classes):
    if len(y) == 0:
        return dict(n=0, macro_f1=None, accuracy=None, gt_cross_entropy=None,
                    support=[0]*classes, per_class_f1=[None]*classes)
    pred = probabilities.argmax(1)
    cm = np.bincount(y*classes + pred, minlength=classes**2).reshape(classes, classes)
    denominator = cm.sum(0)+cm.sum(1)
    f1 = np.divide(2*np.diag(cm), denominator, out=np.zeros(classes), where=denominator>0)
    return dict(n=len(y), macro_f1=float(f1.mean()), accuracy=float(np.mean(pred == y)),
                gt_cross_entropy=float(-np.log(np.clip(probabilities[np.arange(len(y)), y], 1e-30, 1)).mean()),
                support=cm.sum(1).tolist(), per_class_f1=f1.tolist(), confusion=cm.tolist())


def selection_key(m, epoch):
    return (m['macro_f1'], -m['gt_cross_entropy'], -epoch)


def validate_teacher_meta(meta, expected):
    for key, value in expected.items():
        if meta.get(key) != value:
            raise ValueError(f'Mismatched KD teacher {key}')


def score_groups(y, probabilities, classes, train_overlap, common_unseen):
    if train_overlap.shape != y.shape or common_unseen.shape != y.shape:
        raise ValueError('Evaluation grouping order/shape mismatch')
    if np.any(train_overlap & common_unseen):
        raise ValueError('Common-unseen must exclude all training inputs')
    masks = dict(all=np.ones(len(y), dtype=bool), train_overlap=train_overlap,
                 train_nonoverlap=~train_overlap, common_unseen=common_unseen)
    return {k: metrics(y[m], probabilities[m], classes) for k,m in masks.items()}


@torch.inference_mode()
def logits_for(model, x, device, batch=512):
    model.eval()
    if not len(x):
        return torch.empty((0, model.head.out_features))
    output = []
    for offset in range(0, len(x), batch):
        output.append(model(torch.as_tensor(x[offset:offset+batch], dtype=torch.float32, device=device)).cpu())
    result = torch.cat(output)
    if not torch.isfinite(result).all():
        raise FloatingPointError('Nonfinite evaluation logits')
    return result


def sync(device):
    if device.type == 'cuda':
        torch.cuda.synchronize()


def schedule(optimizer, steps_per_epoch, epochs, warmup_epochs):
    total = steps_per_epoch * epochs
    warm = min(warmup_epochs * steps_per_epoch, max(1, total-1))
    def factor(step):
        if step < warm:
            return (step+1)/warm
        return 0.5*(1+math.cos(math.pi*min(step-warm, total-warm)/(total-warm)))
    return torch.optim.lr_scheduler.LambdaLR(optimizer, factor)


def rng_state(device):
    return dict(cpu=torch.get_rng_state(),
                cuda=torch.cuda.get_rng_state_all() if device.type == 'cuda' else [])


def restore_rng(state, device):
    torch.set_rng_state(state['cpu'].cpu())
    if device.type == 'cuda':
        torch.cuda.set_rng_state_all([s.cpu() for s in state['cuda']])


def save_checkpoint(path, model, optimizer, scheduler, meta, epoch, history, device, extra=None):
    payload = dict(model=model.state_dict(), optimizer=optimizer.state_dict(),
                   scheduler=scheduler.state_dict(), rng=rng_state(device),
                   meta=meta, epoch=epoch, history=history, extra=extra or {})
    tmp = path.with_suffix('.tmp')
    torch.save(payload, tmp)
    tmp.replace(path)


def load_checkpoint(path, model, optimizer=None, scheduler=None, device=None):
    payload = torch.load(path, map_location='cpu', weights_only=True)
    model.load_state_dict(payload['model'], strict=True)
    if optimizer is not None:
        optimizer.load_state_dict(payload['optimizer'])
    if scheduler is not None:
        scheduler.load_state_dict(payload['scheduler'])
    if device is not None:
        restore_rng(payload['rng'], device)
    return payload


def checked_step(model, optimizer, scheduler, x, y, teacher_logits, alpha, temperature):
    model.train()
    optimizer.zero_grad(set_to_none=True)
    loss = kd_loss(model(x), y, teacher_logits, alpha, temperature)
    if not torch.isfinite(loss):
        raise FloatingPointError('Nonfinite training loss')
    loss.backward()
    if not all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None):
        raise FloatingPointError('Nonfinite gradient; do not silently freeze GeM or change architecture')
    optimizer.step()
    scheduler.step()
    return float(loss.detach())


def fit_network(kind, train, val, cfg, output, cohort, seed, budget, lr, epochs,
                device='cpu', teacher_checkpoint=None, alpha=0.0, temperature=1.0,
                phase='smoke', warmup_epochs=None, time_limit=600, resume_from=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    classes = cfg['cohorts'][cohort]['classes']
    device = torch.device(device)
    if device.type == 'cuda':
        if not torch.cuda.is_available():
            raise ValueError('CUDA requested but unavailable; no silent CPU fallback')
        # User authorized A100/other Colab GPUs on 2026-10-30. Preserve FP32.
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
    torch.set_num_threads(cfg['training']['cpu_threads'])
    torch.use_deterministic_algorithms(True)
    allowed_lrs = cfg['training']['lr_candidates'][kind if kind in ['M1','M2'] else 'student']
    if lr not in allowed_lrs:
        raise ValueError('LR outside agreed candidates')
    if phase == 'main' and not cfg['training']['epochs_frozen']:
        raise ValueError('Freeze development-selected settings before main training')
    counts = np.bincount(train['y'], minlength=len(classes))
    if not np.all(counts == budget) or np.intersect1d(train['id'], val['id']).size:
        raise ValueError('Incorrect label budget or source-ID overlap')
    batch = cfg['training']['batch_size']
    steps = math.ceil(len(train['y'])/batch)
    warmup_epochs = cfg['training']['warmup_epochs'] if warmup_epochs is None else warmup_epochs
    model = make_model(kind, len(classes), seed, cfg).to(device)
    initial_hash = state_digest(model)
    initial_bn = {n: p.clone() for n, p in model.named_buffers() if 'running_' in n or 'num_batches_tracked' in n}
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=cfg['training']['weight_decay'])
    scheduler = schedule(optimizer, steps, epochs, warmup_epochs)
    meta = dict(model=kind, cohort=cohort, classes=classes, seed=seed, budget=budget,
                phase=phase, lr=lr, alpha=alpha, temperature=temperature, total_epochs=epochs,
                steps_per_epoch=steps, device=str(device),
                device_name=torch.cuda.get_device_name(device) if device.type == 'cuda' else 'CPU',
                torch_version=str(torch.__version__), cuda_version=torch.version.cuda,
                config_sha256=digest(HERE/'config.json'),
                initial_state_sha256=initial_hash, train_ids_sha256=hash_bytes(train['id']),
                train_input_sha256=hash_bytes(train['X']), train_labels_sha256=hash_bytes(train['y']),
                validation_ids_sha256=hash_bytes(val['id']),
                source_hashes={p: digest(HERE/p) for p in ['models.py','training.py','data.py']})
    teacher_logits = None
    teacher_seconds = 0.0
    if kind in ['M4', 'M5']:
        if teacher_checkpoint is None:
            raise ValueError('Missing matched teacher')
        if alpha not in cfg['kd']['alpha_candidates'] or temperature not in cfg['kd']['temperature_candidates']:
            raise ValueError('KD outside agreed search grid')
        expected_kind = 'M1' if kind == 'M4' else 'M2'
        payload = torch.load(teacher_checkpoint, map_location='cpu', weights_only=True)
        validate_teacher_meta(payload['meta'], dict(model=expected_kind, cohort=cohort,
            classes=classes, seed=seed, budget=budget, phase=phase,
            train_ids_sha256=meta['train_ids_sha256'], train_input_sha256=meta['train_input_sha256'],
            train_labels_sha256=meta['train_labels_sha256'], config_sha256=meta['config_sha256']))
        teacher = make_model(expected_kind, len(classes), seed, cfg, load_pretrained=False).to(device)
        teacher.load_state_dict(payload['model'], strict=True)
        teacher.eval().requires_grad_(False)
        t = time.perf_counter()
        teacher_logits = logits_for(teacher, train['X'], device)
        sync(device)
        teacher_seconds = time.perf_counter()-t
        meta['teacher_checkpoint_sha256'] = digest(teacher_checkpoint)
        save_npz(output/'teacher_logits.npz', id=train['id'], logits=teacher_logits.numpy())
        del teacher
    elif teacher_checkpoint is not None or alpha != 0:
        raise ValueError('Direct training cannot consume a teacher')
    # Teacher construction/prediction must not influence the student's RNG stream.
    torch.manual_seed(seed + 30000)
    x = torch.as_tensor(train['X'], dtype=torch.float32, device=device)
    y = torch.as_tensor(train['y'], dtype=torch.long, device=device)
    if teacher_logits is not None:
        teacher_logits = teacher_logits.to(device)
    history, first_epoch, best_key = [], 0, None
    if resume_from is not None:
        p = load_checkpoint(resume_from, model, optimizer, scheduler, device)
        for field in ['model','seed','budget','lr','alpha','temperature','total_epochs','cohort',
                      'phase','train_ids_sha256','train_input_sha256','train_labels_sha256',
                      'validation_ids_sha256','config_sha256','source_hashes']:
            if p['meta'][field] != meta[field]:
                raise ValueError(f'Resume contract mismatch: {field}')
        history, first_epoch = p['history'], p['epoch']
        best_key = max((selection_key(h['validation'],h['epoch']) for h in history), default=None)
        if history and not (output/'best.pt').exists():
            raise ValueError('Resume requires the preserved best checkpoint, too')
    started = time.perf_counter()
    total_steps = first_epoch*steps
    for epoch in range(first_epoch, epochs):
        g = torch.Generator().manual_seed(seed*100000 + epoch)
        permutation = torch.randperm(len(y), generator=g).to(device)
        losses = []
        sync(device)
        t = time.perf_counter()
        for indices in permutation.split(batch):
            losses.append(checked_step(model, optimizer, scheduler, x[indices], y[indices],
                                       None if teacher_logits is None else teacher_logits[indices], alpha, temperature))
            total_steps += 1
        sync(device)
        fitting_seconds = time.perf_counter()-t
        t = time.perf_counter()
        vl = logits_for(model, val['X'], device)
        score = metrics(val['y'], vl.softmax(1).numpy(), len(classes))
        score['gt_cross_entropy'] = float(F.cross_entropy(vl, torch.as_tensor(val['y'], dtype=torch.long)))
        entry = dict(epoch=epoch+1, train_loss=float(np.mean(losses)), validation=score,
                     fitting_seconds=fitting_seconds, validation_seconds=time.perf_counter()-t,
                     updates=total_steps)
        history.append(entry)
        key = selection_key(score, epoch+1)
        if best_key is None or key > best_key:
            best_key = key
            save_checkpoint(output/'best.pt', model, optimizer, scheduler, meta, epoch+1, history, device)
        save_checkpoint(output/'last.pt', model, optimizer, scheduler, meta, epoch+1, history, device)
        write_json(output/'progress.json', dict(model=kind, epoch=epoch+1, total_epochs=epochs,
                   validation_macro_f1=score['macro_f1'], elapsed_seconds=time.perf_counter()-started))
        print(f'{kind} epoch {epoch+1}/{epochs}, finite loss, validation macro-F1={score["macro_f1"]:.4f}', flush=True)
        if time.perf_counter()-started > time_limit and epoch+1 < epochs:
            raise TimeoutError('Time budget reached; last/best checkpoints preserved')
    bn_unchanged = all(torch.equal(initial_bn[n], p) for n,p in model.named_buffers() if n in initial_bn)
    if kind == 'M2' and not bn_unchanged:
        raise AssertionError('M2 pretrained BN running statistics changed')
    if kind == 'M1' and bn_unchanged:
        raise AssertionError('M1 BN statistics never updated')
    best = load_checkpoint(output/'best.pt', model)
    predictions = logits_for(model, val['X'], device).softmax(1).numpy()
    save_npz(output/'validation_predictions.npz', id=val['id'], y=val['y'], probabilities=predictions)
    result = dict(**meta, parameters=sum(p.numel() for p in model.parameters()),
                  selected_epoch=best['epoch'], completed_epochs=len(history),
                  history=history, validation=best['history'][-1]['validation'],
                  teacher_prediction_seconds=teacher_seconds, elapsed_seconds=time.perf_counter()-started,
                  bn_statistics_unchanged=bn_unchanged, best_checkpoint_sha256=digest(output/'best.pt'),
                  last_checkpoint_sha256=digest(output/'last.pt'),
                  performance_result=False if phase == 'smoke' else True)
    write_json(output/'metrics.json', result)
    return model, result


def hash_bytes(a):
    import hashlib
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def fit_m0(train, val, cfg, output, seed, num_leaves=15, max_rounds=None, patience=None):
    import lightgbm as lgb
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    x, names = statistics(train['X'])
    vx, _ = statistics(val['X'])
    c = int(train['y'].max())+1
    settings = cfg['m0']
    if num_leaves not in settings['num_leaves_candidates']:
        raise ValueError('M0 complexity outside agreed candidates')
    params = dict(objective='multiclass', num_class=c, metric='None',
                  learning_rate=settings['learning_rate'], num_leaves=num_leaves,
                  min_data_in_leaf=settings['min_child_samples'], lambda_l2=settings['reg_lambda'],
                  num_threads=settings['num_threads'], seed=seed, deterministic=True,
                  force_col_wise=True, verbosity=-1)
    trainset = lgb.Dataset(x, label=train['y'])
    validset = lgb.Dataset(vx, label=val['y'], reference=trainset)
    history = []
    best = dict(key=None, iteration=None)
    def evaluate(pred, dataset):
        m = metrics(val['y'], pred, c)
        iteration = len(history)+1
        history.append(dict(iteration=iteration, validation=m))
        key = selection_key(m, iteration)
        if best['key'] is None or key > best['key']:
            best.update(key=key, iteration=iteration)
        return [('macro_f1', m['macro_f1'], True)]
    booster = lgb.train(params, trainset, num_boost_round=max_rounds or settings['max_boost_rounds'],
                        valid_sets=[validset], feval=evaluate,
                        callbacks=[lgb.early_stopping(patience or settings['patience'], first_metric_only=True, verbose=False)],
                        keep_training_booster=True)
    # Preserve CE tie-break even when LightGBM's own best_iteration uses F1 alone.
    booster.save_model(str(output/'last.txt'), num_iteration=booster.current_iteration())
    booster.save_model(str(output/'best.txt'), num_iteration=best['iteration'])
    reloaded = lgb.Booster(model_file=str(output/'best.txt'))
    expected = booster.predict(vx, num_iteration=best['iteration'])
    actual = reloaded.predict(vx, num_threads=settings['num_threads'])
    if not np.array_equal(expected, actual):
        raise AssertionError('M0 reload changed predictions')
    save_npz(output/'validation_predictions.npz', id=val['id'], y=val['y'], probabilities=actual)
    result = dict(model='M0', features=names, settings=params, train_ids_sha256=hash_bytes(train['id']),
                  validation_ids_sha256=hash_bytes(val['id']), selected_iteration=best['iteration'],
                  completed_iterations=len(history), history=history, reload_exact=True,
                  validation=metrics(val['y'], actual, c), elapsed_seconds=time.perf_counter()-started,
                  best_checkpoint_sha256=digest(output/'best.txt'))
    write_json(output/'metrics.json', result)
    return reloaded, result
