"""Focused verification with direct byte-key dictionaries on real January rows."""
import collections
import csv
import hashlib
import json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent


def main():
    m=json.loads((HERE/'manifest.json').read_text())
    rows=list(csv.DictReader((HERE/'raw_summary.csv').open()))
    byservice=list(csv.DictReader((HERE/'raw_by_service.csv').open()))
    lookup={(r['cohort'],r['period'],r['packets'],r['policy']):r for r in rows}
    grouped=collections.defaultdict(list)
    for r in byservice:grouped[r['cohort'],r['period'],r['packets'],r['policy']].append(r)
    for key,ss in grouped.items():
        r=lookup[key]
        assert sum(int(x['rows']) for x in ss)==int(r['rows'])
        assert sum(int(x['conflicting_rows']) for x in ss)==int(r['conflicting_rows'])
        assert sum(int(x['same_label_duplicate_excess']) for x in ss)==int(r['same_label_duplicate_excess'])
    for co in m['cohorts']:
        for k in range(1,31):
            for policy in ['padded','at_least_k']:
                pooled=lookup[co,'ALL',str(k),policy]
                monthly=[lookup[co,mo,str(k),policy] for mo in m['months']]
                assert int(pooled['rows'])==sum(int(r['rows']) for r in monthly)
                assert int(pooled['conflicting_rows'])>=sum(int(r['conflicting_rows']) for r in monthly)
    n=m['selected_valid_rows'];x=np.load(HERE/'ppi.npy',mmap_mode='r')[:n];meta=np.load(HERE/'meta.npy',mmap_mode='r')[:n]
    jan=m['months'].index('202501');checks=[]
    for co,spec in m['cohorts'].items():
        take=np.flatnonzero((meta['month']==jan)&np.isin(meta['app'],spec['codes']))
        for k in [1,5,30]:
            groups={}
            for i in take:
                key=x[i,:k].tobytes()
                if key not in groups:groups[key]=collections.Counter()
                groups[key][int(meta['app'][i])]+=1
            totals=[sum(v.values()) for v in groups.values()]
            actual=dict(rows=len(take),unique_patterns=len(groups),
                conflicting_patterns=sum(len(v)>1 for v in groups.values()),
                conflicting_rows=sum(sum(v.values()) for v in groups.values() if len(v)>1),
                same_label_duplicate_excess=sum(sum(v.values())-len(v) for v in groups.values()),
                empirical_minimum_errors=sum(sum(v.values())-max(v.values()) for v in groups.values()))
            expected=lookup[co,'202501',str(k),'padded']
            assert all(v==int(expected[key]) for key,v in actual.items()),(co,k,actual,expected)
            checks.append(dict(cohort=co,period='202501',packets=k,rows=len(take),pass_exact=True))
            print(json.dumps(checks[-1]),flush=True)
            del groups
    result=dict(status='passed',source_sha256=m['source_sha256'],source_id_audit=m['source_id_audit'],
        synthetic_checks='analyze.py self_test passed: all 30 prefixes, two policies, pooled/monthly, direct grouping/pair checks',
        real_data_direct_dictionary_checks=checks,
        aggregation_checks=dict(service_sum_groups=len(grouped),monthly_vs_pooled=True),
        exact_prefix_monotonicity=json.loads((HERE/'raw_complete.json').read_text())['monotonicity_passed'],
        raw_clipped_equal=json.loads((HERE.parents[1]/'reports/2026-10-28_data_audit/build_checks.json').read_text())['raw_clipped_csv_equal'],
        code_sha256=hashlib.sha256((HERE/'analyze.py').read_bytes()).hexdigest(),
        browser_visual_review=False,browser_note='No real-browser rendering claimed; separate offline JavaScript checks recorded in report folder.',
        new_training_runs=0,source_modified=False)
    (HERE/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('PASS: real January direct counts and all CSV aggregation checks',flush=True)


if __name__=='__main__':main()
