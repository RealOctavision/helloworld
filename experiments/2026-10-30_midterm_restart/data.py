"""Prepare exact, January-only cleaned training manifests; no model fitting.

Reuse the audited integer PPI cache. Equality is full canonical array bytes,
not a rounded representation or an unchecked digest. Future labels never
participate in training curation. See config.json and restart_decisions.md.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)


def load_config():
    return json.loads((HERE / 'config.json').read_text())


def canonical(x):
    """Input/output [N,3,30], integer ms / direction / bytes; zero padding."""
    x = np.array(x, dtype='<i4', order='C', copy=True)
    if x.ndim != 3 or x.shape[1:] != (3, 30):
        raise ValueError('Expected N x 3 x 30 PPI')
    active = x[:, 1] != 0
    x[:, 0] = np.clip(x[:, 0], 0, 65000)
    x[:, 2] = np.clip(x[:, 2], 1, 1500)
    x *= active[:, None, :]
    return x


def exact_keys(x):
    a = np.ascontiguousarray(x, dtype='<i4')
    return a.reshape(len(a), 90).view('V360').ravel()


def contains(keys, reference):
    ref = np.unique(reference)
    if not len(ref):
        return np.zeros(len(keys), dtype=bool)
    pos = np.searchsorted(ref, keys)
    return (pos < len(ref)) & (ref[np.minimum(pos, len(ref)-1)] == keys)


def curate(x, labels, ids):
    """Representative = smallest source ID, quarantine ALL conflicting labels."""
    if len(np.unique(ids)) != len(ids):
        raise ValueError('Repeated source ID')
    order = np.argsort(ids, kind='stable')
    keys = exact_keys(x[order])
    _, first, inverse, counts = np.unique(keys, return_index=True,
                                         return_inverse=True, return_counts=True)
    lows = np.full(len(first), np.iinfo(np.int64).max, dtype=np.int64)
    highs = np.full(len(first), -1, dtype=np.int64)
    np.minimum.at(lows, inverse, labels[order])
    np.maximum.at(highs, inverse, labels[order])
    bad = lows != highs
    representatives = order[first]
    keep = np.sort(representatives[~bad])
    audit = dict(id=ids[order], label=labels[order],
                 representative_id=ids[representatives[inverse]],
                 group_size=counts[inverse], conflicting=bad[inverse],
                 kept=np.isin(order, keep))
    return keep, audit, dict(input_rows=len(ids), exact_groups=len(first),
                            conflicting_groups=int(bad.sum()),
                            conflicting_rows=int(bad[inverse].sum()),
                            same_label_duplicate_excess=int((counts[~bad]-1).sum()),
                            retained_unique_inputs=len(keep))


def sample_per_class(y, maximum, seed, require_full=False):
    rng = np.random.default_rng(seed)
    indices, ranks = [], []
    for label in range(int(y.max())+1):
        rows = np.flatnonzero(y == label)
        if require_full and len(rows) < maximum:
            raise ValueError(f'Class {label}: {len(rows)} < {maximum}')
        selected = rng.permutation(rows)[:maximum]
        indices.extend(selected)
        ranks.extend(range(len(selected)))
    return np.asarray(indices, dtype='i8'), np.asarray(ranks, dtype='i4')


def save_npz(path, **arrays):
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('wb') as f:
        np.savez_compressed(f, **arrays)
    tmp.replace(path)


def read_split(cohort, name, budget=None):
    path = HERE / 'prepared' / cohort / f'{name}.npz'
    manifest = json.loads((HERE / 'prepared' / 'manifest.json').read_text())
    expected = manifest['artifacts'][str(path.relative_to(HERE / 'prepared'))]
    if digest(path) != expected or digest(HERE/'config.json') != manifest['config_sha256']:
        raise ValueError('Prepared input or config was modified')
    with np.load(path, allow_pickle=False) as f:
        a = dict(f)
    if budget is not None:
        selected = a['rank'] < budget
        a = {key: value[selected] for key, value in a.items()}
        counts = np.bincount(a['y'])
        if not np.all(counts == budget):
            raise ValueError(f'Wrong class balance in {path}: {counts}')
    return a


def prepare():
    cfg = load_config()
    dest = HERE / 'prepared'
    dest.mkdir(exist_ok=True)
    complete = dest / 'manifest.json'
    if complete.exists():
        m = json.loads(complete.read_text())
        if m['config_sha256'] != digest(HERE / 'config.json'):
            raise ValueError('Config changed after preparation; preserve existing data')
        for path, expected in m['artifacts'].items():
            if digest(dest / path) != expected:
                raise ValueError(f'Artifact changed: {path}')
        print('Prepared manifests already verified; not regenerated.', flush=True)
        return m
    start = time.perf_counter()
    audit_dir = (HERE / cfg['audit_dir']).resolve()
    audit = json.loads((audit_dir / 'manifest.json').read_text())
    source = ROOT / cfg['source']
    if digest(source) != cfg['source_sha256']:
        raise ValueError('Source HDF5 has changed')
    meta = np.load(audit_dir / 'meta.npy', mmap_mode='r')[:audit['selected_valid_rows']]
    ppi = np.load(audit_dir / 'ppi.npy', mmap_mode='r')[:len(meta)]
    m = dict(config_sha256=digest(HERE / 'config.json'),
             source_sha256=cfg['source_sha256'], source_modified=False,
             audit_manifest_sha256=digest(audit_dir / 'manifest.json'),
             cache_sha256={p: digest(audit_dir / p) for p in ['ppi.npy', 'meta.npy']},
             equality='Exact canonical little-endian int32 [IPT,DIR,SIZE] x 30 bytes',
             selection_labels='January only; validation/test labels never curate training',
             source_id_scope='Global unique IDs verified in original audit; split intersections rechecked here. Session-level disjointness is not established.',
             evaluation_scores_computed=False, cohorts={})
    for name, cohort in cfg['cohorts'].items():
        cdir = dest / name
        cdir.mkdir(exist_ok=True)
        classes, codes = cohort['classes'], cohort['codes']
        report = dict(classes=classes, codes=codes, month_support={}, runs={})
        months = {}
        for month in [cfg['months']['train'], cfg['months']['validation'], *cfg['months']['evaluation']]:
            selection = np.flatnonzero((meta['month'] == audit['months'].index(month)) &
                                        np.isin(meta['app'], codes))
            mm = meta[selection]
            y = np.full(len(mm), -1, dtype='i8')
            for label, code in enumerate(codes):
                y[mm['app'] == code] = label
            if np.any(y < 0):
                raise ValueError('Class mapping failed')
            months[month] = dict(X=canonical(ppi[selection].transpose(0, 2, 1)),
                                 y=y, id=mm['id'], day=mm['day'], length=mm['length'])
            report['month_support'][month] = np.bincount(y, minlength=len(codes)).tolist()
        jan = months.pop(cfg['months']['train'])
        keep, audit_rows, summary = curate(jan['X'], jan['y'], jan['id'])
        save_npz(cdir / 'january_curation.npz', **audit_rows)
        clean = {key: value[keep] for key, value in jan.items()}
        counts = np.bincount(clean['y'], minlength=len(codes))
        if np.any(counts < max(cfg['budgets'])):
            raise ValueError(f'{name}: fewer than 1000 cleaned inputs: {counts}')
        summary['retained_per_class'] = dict(zip(classes, map(int, counts)))
        summary['label_access_rows'] = len(jan['y'])
        report['january_curation'] = summary
        feb = months.pop(cfg['months']['validation'])
        vi, rank = sample_per_class(feb['y'], cfg['validation_max_per_class'], cfg['validation_seed'])
        val = {key: value[vi] for key, value in feb.items()}
        val['rank'] = rank
        if np.intersect1d(jan['id'], val['id']).size:
            raise ValueError('Source IDs cross train and validation')
        val_keys = exact_keys(val['X'])
        save_npz(cdir / 'validation.npz', **val)
        report['validation_support'] = np.bincount(val['y'], minlength=len(codes)).tolist()
        all_training_keys = []
        run_arrays = {}
        for phase, seeds, maximum in [('development', cfg['development_seeds'], cfg['development_budget']),
                                       ('main', cfg['main_seeds'], max(cfg['budgets']))]:
            for seed in seeds:
                ii, rank = sample_per_class(clean['y'], maximum, seed, require_full=True)
                run = {key: value[ii] for key, value in clean.items()}
                run['rank'] = rank
                key = f'{phase}_seed{seed}'
                save_npz(cdir / f'{key}.npz', **run)
                run_arrays[key] = run
                rk = exact_keys(run['X'])
                all_training_keys.append(rk)
                report['runs'][key] = dict(rows=len(ii), per_class=maximum,
                    nested_budget_rule='rank < budget',
                    validation_overlap_rows=int(contains(val_keys, rk).sum()))
        union_keys = np.unique(np.concatenate(all_training_keys + [val_keys]))
        report['common_unseen_exclusion'] = 'All preregistered main seeds up to 1000/class, development seeds up to 200/class, and fixed validation. Never the unselected January pool.'
        seen_ids = [jan['id'], val['id']]
        for month, evaluation in months.items():
            for other in seen_ids:
                if np.intersect1d(evaluation['id'], other).size:
                    raise ValueError('Source IDs cross time splits')
            seen_ids.append(evaluation['id'])
            ek = exact_keys(evaluation['X'])
            groups = dict(id=evaluation['id'], validation_overlap=contains(ek, val_keys),
                          common_unseen=~contains(ek, union_keys),
                          short_flow=evaluation['length'] < 30)
            for seed in cfg['main_seeds']:
                run = run_arrays[f'main_seed{seed}']
                rk = exact_keys(run['X'])
                for budget in cfg['budgets']:
                    groups[f'seed{seed}_n{budget}_train_overlap'] = contains(ek, rk[run['rank'] < budget])
            save_npz(cdir / f'evaluation_{month}.npz', **evaluation)
            save_npz(cdir / f'evaluation_groups_{month}.npz', **groups)
            report[f'evaluation_{month}'] = dict(rows=len(ek), groups={
                k: int(v.sum()) for k, v in groups.items() if k != 'id'})
        write_json(cdir / 'manifest.json', report)
        m['cohorts'][name] = report
        print(json.dumps(dict(cohort=name, clean_rows=summary['retained_unique_inputs'],
                              minimum=int(counts.min()), elapsed_seconds=round(time.perf_counter()-start, 1))), flush=True)
        del months, jan, clean, run_arrays, all_training_keys
    m['artifacts'] = {str(p.relative_to(dest)): digest(p) for p in sorted(dest.glob('*/*')) if p.is_file()}
    m['preparation_seconds'] = time.perf_counter()-start
    write_json(complete, m)
    return m


def self_test():
    x = np.zeros((6, 3, 30), dtype='i4')
    x[:, 1, :2] = 1
    x[:, 2, :2] = 100
    x[3:, 0, 1] = [1, 2, 3]
    # Group0: same PPI, different labels -> every row quarantined.
    keep, audit, summary = curate(x, np.array([0, 0, 1, 1, 1, 1]), np.arange(6)+10)
    assert keep.tolist() == [3, 4, 5] and summary['conflicting_rows'] == 3
    # Same-label duplicates collapse to minimum ID, independent of input order.
    keep, _, _ = curate(x[:2], np.array([0, 0]), np.array([20, 10]))
    assert keep.tolist() == [1]
    # Equality ignores labels, padding remains zero, 0ms is a valid packet.
    z = canonical(x)
    assert np.array_equal(z[:, 1] != 0, x[:, 1] != 0)
    assert contains(exact_keys(z), exact_keys(z[:1])).tolist() == [True, True, True, False, False, False]
    y = np.repeat(np.arange(2), 10)
    ii, rank = sample_per_class(y, 8, 7, True)
    assert set(ii[rank < 3]) <= set(ii[rank < 5]) <= set(ii)
    print('Exact curation, source-ID representative, overlap and nesting checks passed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['prepare', 'self-test'])
    args = parser.parse_args()
    self_test() if args.command == 'self-test' else prepare()
