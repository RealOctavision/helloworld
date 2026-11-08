"""Evaluate the four preserved February-selected checkpoints; never fit or tune."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import argparse
import json
import platform
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch
import run as wide
import colab_continuation as evaluator
from colab_main import compact_metrics
from data import digest, read_split, write_json
from training import hash_bytes, load_checkpoint, logits_for

HERE = Path(__file__).resolve().parent
OUTPUT = HERE/'final_evaluation'
MONTHS = ('202504', '202505')
CASES = ((200, 201), (200, 202), (1000, 201), (1000, 202))
EVALUATOR_HASHES = {
    'colab_main.py': 'fd7d7b50f5ba9dcfcf577fda861a267c22426673aa6a31d13467b30567489e4a',
    'colab_continuation.py': '9cb0eabde55cb7bfa64d5649e70ce2c85f996625214c460c8f419a8dc117bf36',
}


def factory(kind, classes, seed, cfg, load_pretrained=False):
    if load_pretrained:
        raise ValueError('No pretrained teacher in this evaluation')
    return wide.make_wide_model(kind, classes, seed, cfg)


def masks_for(data, groups, budget, seed):
    if not np.array_equal(data['id'], groups['id']):
        raise ValueError('Evaluation/group IDs differ')
    overlap = groups[f'seed{seed}_n{budget}_train_overlap']
    unseen = groups['common_unseen']
    if overlap.shape != data['y'].shape or unseen.shape != overlap.shape or np.any(overlap & unseen):
        raise ValueError('Invalid evaluation grouping')
    return dict(all=np.ones(len(overlap), bool), train_overlap=overlap,
                train_nonoverlap=~overlap, common_unseen=unseen)


def verify_prediction_file(folder, data, groups, budget, seed):
    record = json.loads((folder/'metrics.json').read_text())
    if digest(folder/'predictions.npz') != record['prediction_sha256']:
        raise ValueError('Saved predictions changed')
    with np.load(folder/'predictions.npz', allow_pickle=False) as z:
        if not np.array_equal(z['id'], data['id']) or not np.array_equal(z['y'], data['y']):
            raise ValueError('Saved prediction IDs/labels differ')
        if not np.isfinite(z['true_log_probability']).all():
            raise ValueError('Nonfinite saved predictions')
        for group, mask in masks_for(data, groups, budget, seed).items():
            score = compact_metrics(z['y'][mask], z['predicted_label'][mask], z['true_log_probability'][mask], 20)
            if score != record['groups'][group]:
                raise ValueError('Stored metrics do not match predictions')
    return record


def published_records():
    records = {}
    for budget, directory in [(200, wide.BASE/'main_recovered'),
                              (1000, wide.BASE/'continuation_recovered/mixed_n1000')]:
        paths = list(directory.glob('evaluation_*/verified_evaluation.json'))
        if len(paths) != 1:
            raise ValueError('Ambiguous or missing baseline evaluation')
        verified = json.loads(paths[0].read_text())
        if verified['verified'] is not True:
            raise ValueError('Baseline evaluation is not verified')
        for record in verified['records']:
            if record['model'] == 'M3' and (budget, record['seed']) in CASES:
                key = (record['month'], budget, record['seed'])
                if key in records or record['budget'] != budget:
                    raise ValueError('Duplicate/mismatched baseline')
                records[key] = record
    if set(records) != {(m, b, s) for m in MONTHS for b, s in CASES}:
        raise ValueError('Missing paired baselines')
    return records


def summarize(rows):
    result = []
    for month in MONTHS:
        for budget in (200, 1000):
            for group in ('all', 'common_unseen'):
                selected = [r for r in rows if (r['month'], r['budget'], r['group']) == (month, budget, group)]
                if len(selected) != 2:
                    continue
                result.append(dict(month=month, budget=budget, group=group, seeds=[201, 202], n=selected[0]['n'],
                    **{key: float(np.mean([r[key] for r in selected])) for key in (
                        'wide_macro_f1', 'baseline_macro_f1', 'delta_f1_pp',
                        'wide_accuracy', 'baseline_accuracy', 'delta_accuracy_pp')}))
    return result


def run_evaluation():
    cfg, frozen = wide.settings()
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA required for the preserved evaluation routine')
    for name, expected in EVALUATOR_HASHES.items():
        if digest(wide.BASE/name) != expected:
            raise ValueError('Original evaluator changed: '+name)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    old = published_records()
    val = read_split(wide.COHORT, 'validation')
    checkpoints = {}
    for budget, seed in CASES:
        folder = HERE/'runs'/f'M3_wide_s{seed}_n{budget}'
        metric = wide.completed_result(folder)
        context = json.loads((folder/'run_context.json').read_text())
        if metric is None or metric['completed_epochs'] != 50 or context['source_hashes']['runner'] != digest(HERE/'run.py'):
            raise ValueError('Incomplete or changed training run')
        hashes = wide.split_hashes(read_split(wide.COHORT, f'main_seed{seed}', budget), val)
        if any(context[k] != v for k, v in hashes.items()):
            raise ValueError('Training or validation data changed')
        paired = wide.baseline(seed, budget, hashes)
        original_training = json.loads((wide.BASE/paired['path']).read_text())
        for month in MONTHS:
            if old[month, budget, seed]['checkpoint_sha256'] != original_training['best_checkpoint_sha256']:
                raise ValueError('Baseline test record belongs to a different checkpoint')
        cp = folder/'best.pt'
        model = factory(wide.KIND, 20, seed, cfg).to('cuda')
        payload = load_checkpoint(cp, model)
        if payload['epoch'] != metric['selected_epoch']:
            raise ValueError('Checkpoint is not the February-selected epoch')
        repeated = logits_for(model, val['X'], torch.device('cuda')).softmax(1).numpy()
        with np.load(folder/'validation_predictions.npz', allow_pickle=False) as z:
            np.testing.assert_array_equal(z['id'], val['id'])
            np.testing.assert_array_equal(z['y'], val['y'])
            np.testing.assert_allclose(repeated, z['probabilities'], atol=1e-6, rtol=1e-5)
            np.testing.assert_array_equal(repeated.argmax(1), z['probabilities'].argmax(1))
        checkpoints[f'M3_wide_s{seed}_n{budget}'] = dict(sha256=digest(cp), selected_epoch=payload['epoch'])
        del model
    protocol = dict(checkpoints=checkpoints, months=list(MONTHS), cases=list(map(list, CASES)),
        selection='Preserved February-selected best.pt; no retraining or post-test selection',
        primary='April all', temporal='May all', secondary='common_unseen and overlap groups',
        code_sha256=digest(Path(__file__)), evaluator_hashes=EVALUATOR_HASHES,
        python=platform.python_version(), torch=str(torch.__version__), numpy=np.__version__,
        cuda=torch.version.cuda, device=torch.cuda.get_device_name(0), precision='FP32, TF32 disabled',
        batch_size=frozen['evaluation']['batch_size'])
    wide.bind_context(OUTPUT, protocol)
    protocol_sha = digest(OUTPUT/'run_context.json')
    rows = []
    started = time.monotonic()
    def check_budget():
        if time.monotonic()-started > 20*60:
            raise TimeoutError('Evaluation time limit; completed files are reusable')
    for month in MONTHS:
        data = read_split(wide.COHORT, f'evaluation_{month}')
        groups = read_split(wide.COHORT, f'evaluation_groups_{month}')
        hashes = {f'evaluation_{field}_sha256': hash_bytes(data[key])
                  for field, key in [('ids', 'id'), ('input', 'X'), ('labels', 'y')]}
        for budget, seed in CASES:
            name = f'M3_wide_s{seed}_n{budget}'
            cp = HERE/'runs'/name/'best.pt'
            baseline = old[month, budget, seed]
            if baseline['classes'] != cfg['cohorts'][wide.COHORT]['classes'] or any(baseline[k] != v for k, v in hashes.items()):
                raise ValueError('Baseline test inputs/labels/order differ')
            if digest(cp) != checkpoints[name]['sha256']:
                raise ValueError('Checkpoint changed after freeze')
            masks = masks_for(data, groups, budget, seed)
            for group, mask in masks.items():
                if int(mask.sum()) != baseline['groups'][group]['n']:
                    raise ValueError('Baseline test group differs')
            folder = OUTPUT/month/name
            with patch.object(evaluator, 'make_model', factory):
                evaluator.eval_one(wide.KIND, seed, budget, wide.COHORT, cp, folder,
                    cfg, frozen, protocol_sha, data, groups, None, check_budget)
            result = verify_prediction_file(folder, data, groups, budget, seed)
            for group, score in result['groups'].items():
                base_score = baseline['groups'][group]
                if score['support'] != base_score['support']:
                    raise ValueError('Baseline class support differs')
                rows.append(dict(month=month, budget=budget, seed=seed, group=group, n=score['n'],
                    wide_macro_f1=score['macro_f1'], baseline_macro_f1=base_score['macro_f1'],
                    wide_accuracy=score['accuracy'], baseline_accuracy=base_score['accuracy'],
                    delta_f1_pp=None if score['n']==0 else 100*(score['macro_f1']-base_score['macro_f1']),
                    delta_accuracy_pp=None if score['n']==0 else 100*(score['accuracy']-base_score['accuracy'])))
            print('EVALUATED', month, name, json.dumps(rows[-4]), flush=True)
            write_json(OUTPUT/'summary.json', dict(status='running', completed=len(rows)//4, planned=8,
                rows=rows, means=summarize(rows), protocol_sha256=protocol_sha))
        del data, groups
    summary = dict(status='completed', completed=8, planned=8, rows=rows, means=summarize(rows),
        protocol_sha256=protocol_sha, seconds=time.monotonic()-started,
        notes=['Two paired seeds, not five-seed baseline means', 'Baseline trained/evaluated on A100; wide on T4',
               'No test scores used to choose weights; future tuning would make these reused test sets'])
    write_json(OUTPUT/'summary.json', summary)
    print(json.dumps(dict(status=summary['status'], completed=8, means=summary['means']), indent=2), flush=True)


def self_test():
    import tempfile
    cfg, frozen = wide.settings()
    x = np.zeros((40, 3, 30), dtype='i4')
    x[:, 1, :10] = 1
    x[:, 2, :10] = np.arange(40)[:, None]+100
    data = dict(id=np.arange(40), X=x, y=np.arange(40)%20)
    groups = dict(id=data['id'].copy(), seed201_n200_train_overlap=np.arange(40)<4, common_unseen=np.arange(40)>=8)
    with tempfile.TemporaryDirectory() as temp:
        cp = Path(temp)/'best.pt'
        model = factory(wide.KIND, 20, 201, cfg).to('cuda')
        torch.save(dict(model=model.state_dict(), epoch=1), cp)
        out = Path(temp)/'202504'/'M3_wide_s201_n200'
        with patch.object(evaluator, 'make_model', factory):
            evaluator.eval_one(wide.KIND, 201, 200, wide.COHORT, cp, out, cfg, frozen, 'synthetic', data, groups, None, lambda: None)
        record = verify_prediction_file(out, data, groups, 200, 201)
        probability = logits_for(model, x, torch.device('cuda')).softmax(1).numpy()
        expected = wide.training.metrics(data['y'], probability, 20)
        assert record['groups']['all']['macro_f1'] == expected['macro_f1']
        assert record['groups']['all']['accuracy'] == expected['accuracy']
        with patch.object(evaluator, 'make_model', side_effect=AssertionError('Unexpected rerun')):
            evaluator.eval_one(wide.KIND, 201, 200, wide.COHORT, cp, out, cfg, frozen, 'synthetic', data, groups, None, lambda: None)
        for bad_groups in [dict(groups, id=data['id'][::-1]), dict(groups, common_unseen=np.ones(40, bool))]:
            try:
                masks_for(data, bad_groups, 200, 201)
            except ValueError:
                pass
            else:
                raise AssertionError('Bad grouping accepted')
        (out/'predictions.npz').write_bytes(b'corrupt')
        try:
            verify_prediction_file(out, data, groups, 200, 201)
        except ValueError:
            pass
        else:
            raise AssertionError('Corrupt predictions accepted')
    print('PASS: synthetic inference, metric replay, completed reuse, ID/overlap and corruption guards; no fitting')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    self_test() if args.self_test else run_evaluation()
