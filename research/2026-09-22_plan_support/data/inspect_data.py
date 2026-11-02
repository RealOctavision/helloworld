"""Read official XS metadata/support counts; inspect only early-June training PPI.
No model fitting, predictions, or test-performance calculations are performed.
Run with .venv/bin/python inspect_data.py from this directory (or any cwd).
"""
import ast
import csv
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import tables

ROOT = Path(__file__).resolve().parent
PATH = ROOT / 'CESNET-QUICEXT-25-XS.h5'
PERIODS = {
    'train': ('20240601', '20240614'),
    'validation': ('20240615', '20240620'),
    'near_test_support_only': ('20240621', '20240630'),
    'future_2024_09_support_only': ('20240901', '20240930'),
    'future_2024_12_support_only': ('20241201', '20241231'),
    'future_2025_05_support_only': ('20250501', '20250531'),
}


def main():
    assert PATH.stat().st_size == 3544625537, 'Incomplete XS download'
    constants = {}
    for statement in ast.parse((ROOT / 'source/datasets_constants.py').read_text()).body:
        if isinstance(statement, ast.Assign) and statement.targets[0].id.startswith('_CESNET_QUICEXT_25'):
            constants[statement.targets[0].id] = ast.literal_eval(statement.value)
    app_names = constants['_CESNET_QUICEXT_25_TABLES_APP_ENUM']
    expected_dates = constants['_CESNET_QUICEXT_25_AVAILABLE_DATES']
    per_day = {}
    with tables.open_file(PATH, mode='r') as h5:
        nodes = sorted(h5.root.flows._f_iter_nodes(), key=lambda n: n._v_name)
        dates = [n._v_name.removeprefix('D') for n in nodes]
        assert dates == expected_dates
        assert sum(n.nrows for n in nodes) == 10_000_000
        first = nodes[0]
        schema = {name: str(first.dtype[name]) for name in first.colnames}
        assert {v: k for k, v in dict(first.get_enum('APP')).items()} == app_names
        for table in nodes:
            day = table._v_name.removeprefix('D')
            per_day[day] = np.bincount(table.col('APP'), minlength=len(app_names))
        # This single row read is restricted to the first day of the training period.
        rows = first.read(0, 4)
        ppi = rows['PPI'].copy()
        assert ppi.shape == (4, 3, 30)
        assert np.isfinite(ppi).all()
        assert np.isin(ppi[:, 1, :], [-1, 0, 1]).all()
        assert (ppi[:, 0, 0] == 0).all()
        assert not ppi.transpose(0, 2, 1)[ppi[:, 1, :] == 0].any()
        np.save(ROOT / 'june_train_ppi4.npy', ppi)
        np.savez_compressed(ROOT / 'june_train_ppi4.npz', PPI=ppi,
                            APP=rows['APP'], ID=rows['ID'], PPI_LEN=rows['PPI_LEN'],
                            date=np.array(['20240601'] * 4))
        sample = {'date': '2024-06-01', 'app': app_names[int(rows[0]['APP'])],
                  'PPI_LEN': int(rows[0]['PPI_LEN']), 'PPI': ppi[0].tolist()}
    with (ROOT / 'support_by_day_and_class.csv').open('w') as out:
        writer = csv.writer(out)
        writer.writerow(['date', 'total'] + [app_names[i] for i in range(len(app_names))])
        for day, counts in per_day.items():
            writer.writerow([day, int(counts.sum())] + counts.tolist())
    summary = {}
    with (ROOT / 'support_by_period_and_class.csv').open('w') as out:
        writer = csv.writer(out)
        writer.writerow(['APP_code', 'tag'] + list(PERIODS))
        for key, (start, end) in PERIODS.items():
            selected = [d for d in dates if start <= d <= end]
            counts = np.sum([per_day[d] for d in selected], axis=0)
            summary[key] = {'start': start, 'end': end, 'available_days': len(selected),
                            'flows': int(counts.sum()),
                            'class_support': dict(zip(app_names.values(), map(int, counts)))}
        for code, tag in app_names.items():
            writer.writerow([code, tag] + [summary[k]['class_support'][tag] for k in PERIODS])
    start, end = date(2024, 6, 1), date(2025, 5, 31)
    all_dates = [(start + timedelta(days=i)).strftime('%Y%m%d') for i in range((end - start).days + 1)]
    report = {
        'source': PATH.name, 'bytes': PATH.stat().st_size,
        'sha256': hashlib.file_digest(PATH.open('rb'), 'sha256').hexdigest(),
        'rows': sum(int(c.sum()) for c in per_day.values()),
        'first_date': dates[0], 'last_date': dates[-1], 'days': len(dates),
        'missing_dates': sorted(set(all_dates) - set(dates)),
        'schema': schema, 'APP_enum': app_names,
        'sample_scope': 'Four first rows of 2024-06-01, training only; no evaluation performance inspected',
        'ppi_sample_shape': list(ppi.shape), 'ppi_sample_dtype': str(ppi.dtype),
        'sample_without_identifiers': sample,
        'periods': summary,
        'environment': {'python': sys.version, 'numpy': np.__version__, 'tables': tables.__version__},
    }
    (ROOT / 'inspection.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['bytes', 'sha256', 'rows', 'first_date', 'last_date', 'days', 'missing_dates', 'ppi_sample_shape', 'ppi_sample_dtype']}, indent=2))
    print('PASS: real XS read, official APP/date match, PPI4 shape/direction/first-IPT/padding checks')


if __name__ == '__main__':
    main()
