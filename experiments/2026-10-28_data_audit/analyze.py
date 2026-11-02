"""Read-only exact PPI-prefix audit; never trains or modifies the source HDF5.

Run with research/2026-09-22_plan_support/data/.venv/bin/python.
Exact lexicographic grouping uses packet-major bytes, not probabilistic hashes.
All numerical outputs include their denominator and observation policy.
"""
import argparse
import collections
import csv
import hashlib
import itertools
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
import tables

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DATA = ROOT / 'research/2026-09-22_plan_support/data'
SOURCE = DATA / 'CESNET-QUICEXT-25-XS.h5'
MONTHS = [f'2024{m:02}' for m in range(6, 13)] + [f'2025{m:02}' for m in range(1, 6)]
BACKGROUND = {0, 51, 52}
META = np.dtype([('id', '<u4'), ('app', 'u1'), ('month', 'u1'), ('length', 'u1'), ('day', '<u4')])


def save_json(path, obj):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)


def log(stage, **kw):
    obj = {'stage': stage, **kw}
    print(json.dumps(obj, ensure_ascii=False), flush=True)
    save_json(HERE / 'progress.json', obj)


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def csv_write(path, rows):
    if not rows:
        return
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def choose_cohorts():
    sm = list(csv.DictReader((DATA / 'servicemap.csv').open()))
    days = list(csv.DictReader((DATA / 'support_by_day_and_class.csv').open()))
    jan = collections.Counter()
    for r in days:
        if r['date'].startswith('202501'):
            jan.update({k: int(v) for k, v in r.items() if k not in ['date', 'total']})
    with tables.open_file(SOURCE, 'r') as h:
        enum = {k: int(v) for k, v in dict(next(h.root.flows._f_iter_nodes()).get_enum('APP')).items()}
    google = [r['Tag'] for r in sm if r['Service Provider'] == 'google']
    # dns-doh aggregates Google DNS and four other providers; exclude the entire label.
    excluded = set(google) | {'dns-doh'} | {k for k, v in enum.items() if v in BACKGROUND}
    non = sorted((k for k in enum if k not in excluded), key=lambda k: (-jan[k], k))[:20]
    old = json.loads((ROOT / 'experiments/2026-10-05_service20_label_ablation/protocol.json').read_text())
    mixed = old['cohorts']['google20']['classes']
    cohorts = {
        'non_google20': {'title': 'Google 제외 20서비스', 'classes': non,
                         'selection': 'Official provider != google; exclude mixed dns-doh/background; top 20 by January 2025 raw XS counts, ties by tag.'},
        'google_included20': {'title': 'Google 포함 20서비스', 'classes': mixed,
                              'selection': 'Reuse the exact pre-existing google20 class list; no collision-based selection.'},
        'google_family24': {'title': 'Google 계열 24서비스', 'classes': google,
                            'selection': 'All 24 labels with official Service Provider=google, including YouTube; no background.'},
    }
    for c in cohorts.values():
        c['codes'] = [enum[x] for x in c['classes']]
        c['january_raw_support'] = {x: jan[x] for x in c['classes']}
    assert len(non) == len(mixed) == 20 and len(google) == 24
    return enum, cohorts


def prepare():
    manifest_path = HERE / 'manifest.json'
    if manifest_path.exists():
        return json.loads(manifest_path.read_text())
    enum, cohorts = choose_cohorts()
    union = sorted(set(itertools.chain.from_iterable(c['codes'] for c in cohorts.values())))
    day_counts = list(csv.DictReader((DATA / 'support_by_day_and_class.csv').open()))
    names = {v: k for k, v in enum.items()}
    capacity = sum(sum(int(r[names[c]]) for c in union) for r in day_counts)
    pp = np.lib.format.open_memmap(HERE / 'ppi.npy', mode='w+', dtype='<i4', shape=(capacity, 30, 3))
    meta = np.lib.format.open_memmap(HERE / 'meta.npy', mode='w+', dtype=META, shape=(capacity,))
    support = []
    quality = []
    offset = 0
    all_ids = []
    with tables.open_file(SOURCE, 'r') as h:
        nodes = sorted(h.root.flows._f_iter_nodes(), key=lambda t: t.name)
        for di, t in enumerate(nodes):
            day = t.name[1:]
            mi = MONTHS.index(day[:6])
            rows = t.read()
            all_ids.append(rows['ID'].copy())
            x = rows['PPI']
            active = x[:, 1] != 0
            length = active.sum(1)
            pad = ~active
            reasons = {
                'nonfinite': ~np.isfinite(x).all((1, 2)),
                'negative_ipt': (x[:, 0] < 0).any(1),
                'first_ipt_nonzero': x[:, 0, 0] != 0,
                'invalid_direction': ~np.isin(x[:, 1], [-1, 0, 1]).all(1),
                'nonpositive_active_size': (active & (x[:, 2] <= 0)).any(1),
                'nonzero_padding': (pad & (x != 0).any(1)).any(1),
                'nontrailing_padding': (active & (np.cumsum(pad, axis=1) > 0)).any(1),
                'empty_ppi': length == 0,
            }
            valid = ~np.logical_or.reduce(list(reasons.values()))
            flags = dict(reasons,
                ppi_len_mismatch=rows['PPI_LEN'] != length,
                total_packets_below_observed=(rows['PACKETS'].astype('u8') + rows['PACKETS_REV']) < length,
                non_udp=rows['PROTOCOL'] != 17,
                port_not_443=rows['DST_PORT'] != 443,
                empty_sni=rows['QUIC_SNI'] == b'',
                ipt_clipped=((x[:, 0] > 65000) & active).any(1),
                size_clipped=((x[:, 2] > 1500) & active).any(1))
            for code in np.unique(rows['APP']):
                m = rows['APP'] == code
                good = m & valid
                support.append(dict(month=MONTHS[mi], day=day, code=int(code), service=names[int(code)],
                                    rows=int(m.sum()), valid_rows=int(good.sum())))
                quality.append(dict(month=MONTHS[mi], day=day, code=int(code), service=names[int(code)],
                                    rows=int(m.sum()), **{k: int((m & v).sum()) for k, v in flags.items()}))
            keep = valid & np.isin(rows['APP'], union)
            n = int(keep.sum())
            pp[offset:offset+n] = x[keep].transpose(0, 2, 1)
            for col, val in [('id', rows['ID'][keep]), ('app', rows['APP'][keep]),
                             ('month', mi), ('length', length[keep]), ('day', int(day))]:
                meta[col][offset:offset+n] = val
            offset += n
            if di % 30 == 0:
                log('reading_source', day=day, days_done=di+1, days_total=len(nodes), selected_rows=offset)
    pp.flush(); meta.flush()
    ids = np.concatenate(all_ids)
    uid, idcount = np.unique(ids, return_counts=True)
    id_stats = dict(rows=len(ids), unique_ids=len(uid), duplicate_excess_rows=int(len(ids)-len(uid)),
                    repeated_ids=int((idcount > 1).sum()))
    csv_write(HERE / 'support_by_day_service.csv', support)
    csv_write(HERE / 'quality_by_day_service.csv', quality)
    expected = json.loads((DATA / 'inspection.json').read_text())
    actual_sha = digest(SOURCE)
    assert actual_sha == expected['sha256'], 'Original source checksum changed'
    manifest = dict(version=1, date='2026-10-28', source=str(SOURCE.relative_to(ROOT)),
                    source_sha256=actual_sha, source_bytes=SOURCE.stat().st_size,
                    source_rows=len(ids), source_days=len(nodes), missing_days=expected['missing_dates'],
                    months=MONTHS, enum=enum, cohorts=cohorts, selected_union_codes=union,
                    capacity=capacity, selected_valid_rows=offset, source_id_audit=id_stats,
                    equality='Exact integer triples (IPT ms, DIR, SIZE bytes), ordered packet 1..k; label excluded from grouping.',
                    representations={'raw': 'Original PPI; no time crop or scaling.',
                                     'clipped': 'IPT clipped [0,65000], SIZE clipped [1,1500], padding reset to zero; no time crop. This audits the shared pre-model PPI, not teacher internal IPT bins.'},
                    policies={'padded': 'All valid flows, missing packets are zero padded.',
                              'at_least_k': 'Only flows with at least k actual packets; denominator changes with k.'},
                    selection_warning='Cohorts have different class composition; comparisons do not isolate the causal effect of Google membership.',
                    python=sys.version, numpy=np.__version__, pytables=tables.__version__)
    save_json(manifest_path, manifest)
    return manifest


def grouped_statistics(group, labels, codes, support):
    """Rows here come from global repeated-prefix groups; other rows are unique.

    Some repeats may vanish after selecting a cohort/month/length policy. Compute
    counts again after selection, including those now-singleton groups.
    """
    n = int(support.sum())
    keys, counts = np.unique(group.astype('u8') * 64 + labels, return_counts=True)
    g = keys // 64
    c = (keys % 64).astype(int)
    starts = np.r_[0, np.flatnonzero(g[1:] != g[:-1]) + 1] if len(g) else np.array([], dtype=int)
    ng = np.diff(np.r_[starts, len(g)]) if len(g) else np.array([], dtype=int)
    totals = np.add.reduceat(counts, starts) if len(g) else np.array([], dtype=int)
    maxima = np.maximum.reduceat(counts, starts) if len(g) else np.array([], dtype=int)
    conflict = np.repeat(ng > 1, ng)
    row_conflict = np.bincount(c[conflict], weights=counts[conflict], minlength=64).astype('i8')
    same_excess = np.bincount(c, weights=counts-1, minlength=64).astype('i8')
    perclass = []
    for code in codes:
        cn = int(support[code])
        perclass.append(dict(code=int(code), rows=cn, unique_patterns_within_service=cn-int(same_excess[code]),
                             same_label_duplicate_excess=int(same_excess[code]),
                             conflicting_rows=int(row_conflict[code]),
                             conflicting_rate=float(row_conflict[code]/cn) if cn else None))
    unique = n - len(group) + len(starts)
    conflicted = int(counts[conflict].sum())
    summary = dict(rows=n, unique_patterns=int(unique), duplicate_excess_rows=int(n-unique),
                   same_label_duplicate_excess=int(same_excess.sum()), conflicting_patterns=int((ng > 1).sum()),
                   conflicting_rows=conflicted, conflicting_rate=conflicted/n if n else None,
                   empirical_minimum_errors=int((totals-maxima).sum()),
                   empirical_minimum_error_rate=float((totals-maxima).sum()/n) if n else None)
    return summary, perclass, (g[conflict], c[conflict], counts[conflict])


def pair_statistics(compressed, codes):
    g, c, counts = compressed
    byclass = {code: (g[c == code], counts[c == code]) for code in codes if (c == code).any()}
    out = []
    for a, b in itertools.combinations(byclass, 2):
        ga, ca = byclass[a]; gb, cb = byclass[b]
        shared, ia, ib = np.intersect1d(ga, gb, assume_unique=True, return_indices=True)
        if len(shared):
            out.append(dict(code_a=int(a), code_b=int(b), shared_patterns=len(shared),
                            rows_a=int(ca[ia].sum()), rows_b=int(cb[ib].sum()),
                            cross_label_row_pairs=int(np.sum(ca[ia].astype('i8') * cb[ib]))))
    return out


def self_test():
    # A repeated within one service, B ambiguous across services and months, C unique.
    x = np.zeros((6, 30, 3), dtype='<i4')
    x[:, 0] = [0, 1, 1200]
    x[:, 1] = [[1,-1,100], [1,-1,100], [2,-1,100], [2,-1,100], [3,-1,100], [2,-1,100]]
    x[5, 2] = [4,1,200]
    app = np.array([1,1,1,2,2,2], dtype='u1')
    months = np.array([0,1,0,0,1,1])
    lengths = np.array([2,2,2,2,2,3])
    order = np.argsort(x.reshape(len(x),90).view('V360').ravel(), kind='stable')
    boundary = np.zeros(len(x), dtype=bool); boundary[0] = True
    for k in range(1, 31):
        boundary[1:] |= (x[order[1:], k-1] != x[order[:-1], k-1]).any(1)
        gid = np.cumsum(boundary)-1
        dup = np.r_[~boundary[1:], False] | ~boundary
        for month in [-1,0,1]:
            for sufficient in [False,True]:
                selected = ((months[order] == month) if month >= 0 else np.ones(6,dtype=bool))
                if sufficient: selected &= lengths[order] >= k
                take = selected & dup
                support = np.bincount(app[order[selected]], minlength=64)
                got, per, comp = grouped_statistics(gid[take],app[order[take]],[1,2],support)
                brute = collections.defaultdict(list)
                for i in order[selected]: brute[x[i,:k].tobytes()].append(int(app[i]))
                conflict = [v for v in brute.values() if len(set(v)) > 1]
                assert got['rows'] == sum(map(len,brute.values()))
                assert got['unique_patterns'] == len(brute)
                assert got['conflicting_rows'] == sum(map(len,conflict))
                assert got['conflicting_patterns'] == len(conflict)
                assert got['same_label_duplicate_excess'] == sum(len(v)-len(set(v)) for v in brute.values())
                assert got['empirical_minimum_errors'] == sum(len(v)-max(collections.Counter(v).values()) for v in brute.values())
                pairs = pair_statistics(comp,[1,2])
                assert sum(p['cross_label_row_pairs'] for p in pairs) == sum(v.count(1)*v.count(2) for v in conflict)
    z = np.array([[[70000, 1, 1600], [0,0,0]], [[80000,1,1700],[0,0,0]]], dtype='<i4')
    z[:,:,0] = np.clip(z[:,:,0],0,65000); z[:,:,2] = np.clip(z[:,:,2],1,1500)
    z[z[:,:,1]==0] = 0
    assert np.array_equal(z[0],z[1])
    log('self_test_passed', checks='Brute-force all 30 prefixes, two length policies, pooled/monthly, labels/pairs/counts/padding/clipping')


def temporal_overlap(gid, app, month, codes, names):
    out=[]
    # January pool overlap is a source-pool diagnostic, not actual model train/test leakage.
    jan = MONTHS.index('202501')
    ca = np.isin(app, codes)
    ref = ca & (month == jan)
    rg = np.unique(gid[ref]); rkey=np.unique(gid[ref].astype('u8')*64+app[ref])
    rgroup, rcount = np.unique(rkey//64, return_counts=True)
    for mi, m in enumerate(MONTHS):
        if mi == jan: continue
        target = ca & (month == mi)
        tg, ta = gid[target], app[target]
        match=np.isin(tg,rg)
        same=np.isin(tg.astype('u8')*64+ta,rkey)
        # A matching source group has another label when label count > same-label indicator.
        pos=np.searchsorted(rgroup,tg)
        nr=np.zeros(len(tg),dtype=int)
        if len(rgroup):
            safe=np.minimum(pos,len(rgroup)-1)
            hit=(pos<len(rgroup)) & (rgroup[safe]==tg)
            nr[hit]=rcount[safe[hit]]
        different=nr>same.astype(int)
        for code in codes:
            c=ta==code; n=int(c.sum())
            out.append(dict(target_month=m, service=names[code], code=int(code), target_rows=n,
                            match_january_any_label=int((c&match).sum()), match_january_same_label=int((c&same).sum()),
                            match_january_other_label=int((c&different).sum())))
    return out


def analyze_representation(manifest, representation):
    done = HERE / f'{representation}_complete.json'
    if done.exists(): return
    n = manifest['selected_valid_rows']
    original = np.load(HERE/'ppi.npy', mmap_mode='r')[:n]
    meta = np.load(HERE/'meta.npy', mmap_mode='r')[:n]
    data = original
    if representation == 'clipped':
        data = np.lib.format.open_memmap(HERE/'clipped.npy', mode='w+', dtype='<i4', shape=original.shape)
        for start in range(0,n,100000):
            b=original[start:start+100000].copy()
            b[:,:,0]=np.clip(b[:,:,0],0,65000)
            b[:,:,2]=np.clip(b[:,:,2],1,1500)
            b[b[:,:,1]==0]=0
            data[start:start+len(b)]=b
        data.flush()
    log('sorting_exact_bytes', representation=representation, rows=n)
    order = np.argsort(data.reshape(n,90).view('V360').reshape(-1), kind='stable')
    sorted_data = np.lib.format.open_memmap(HERE/'sorted_work.npy',mode='w+',dtype='<i4',shape=data.shape)
    for start in range(0,n,100000): sorted_data[start:start+100000]=data[order[start:start+100000]]
    sorted_data.flush()
    smeta=meta[order]
    app, month, length = smeta['app'], smeta['month'], smeta['length']
    cohorts=manifest['cohorts']; names={v:k for k,v in manifest['enum'].items()}
    boundary=np.zeros(n,dtype=bool); boundary[0]=True
    summaries=[]; services=[]; pairs=[]; examples=[]
    cohortmask={key:np.isin(app,c['codes']) for key,c in cohorts.items()}
    # Precompute denominators by month and exact observed length, independent of collisions.
    hist=np.bincount((month.astype(int)*64+app)*31+length,minlength=12*64*31).reshape(12,64,31)
    csv_write(HERE/'packet_length_by_month_service.csv', [dict(month=MONTHS[m],service=names[c],code=c,packets=l,rows=int(hist[m,c,l])) for m in range(12) for c in manifest['selected_union_codes'] for l in range(31)])
    for k in range(1,31):
        boundary[1:] |= (sorted_data[1:,k-1] != sorted_data[:-1,k-1]).any(1)
        gid=np.cumsum(boundary,dtype='i8')-1
        duplicate=np.r_[~boundary[1:],False] | ~boundary
        positions=np.flatnonzero(duplicate)
        dg,da,dm,dl=gid[positions],app[positions],month[positions],length[positions]
        for co, spec in cohorts.items():
            codes=spec['codes']; dc=np.isin(da,codes)
            for mi in [-1]+list(range(12)):
                period='ALL' if mi<0 else MONTHS[mi]
                byperiod=dc if mi<0 else dc & (dm==mi)
                rawhist=hist.sum(0) if mi<0 else hist[mi]
                for policy in ['padded','at_least_k']:
                    selected=byperiod if policy=='padded' else byperiod & (dl>=k)
                    support=rawhist.sum(1) if policy=='padded' else rawhist[:,k:].sum(1)
                    support=support.copy(); support[~np.isin(np.arange(64),codes)]=0
                    summary, per, compressed=grouped_statistics(dg[selected],da[selected],codes,support)
                    context=dict(representation=representation,cohort=co,period=period,packets=k,policy=policy)
                    summaries.append(dict(**context,**summary))
                    for row in per: services.append(dict(**context,service=names[row['code']],**row))
                    if policy=='padded':
                        for row in pair_statistics(compressed,codes):
                            pairs.append(dict(**context,service_a=names[row['code_a']],service_b=names[row['code_b']],**row))
                    if k==30 and mi<0 and policy=='padded':
                        cg,cc,cn=compressed
                        if len(cg):
                            ug,st=np.unique(cg,return_index=True)
                            totals=np.add.reduceat(cn,st)
                            for j in np.argsort(totals)[-10:][::-1]:
                                g=ug[j]; lo=np.searchsorted(gid,g); hi=np.searchsorted(gid,g,side='right')
                                ids=np.arange(lo,hi)[cohortmask[co][lo:hi]]
                                label_counts={names[int(c)]:int(v) for c,v in zip(cc[cg==g],cn[cg==g])}
                                examples.append(dict(representation=representation,cohort=co,packets=30,rows=int(len(ids)),
                                                     label_counts=label_counts, observed_packets=int(length[ids[0]]),
                                                     prefix_ipt_dir_size=sorted_data[ids[0]].tolist(),
                                                     representative_rows=[dict(source_id=int(smeta['id'][i]),date=int(smeta['day'][i]),service=names[int(app[i])]) for i in ids[:12]]))
        if k in [1,5,10,20,30]:
            csv_write(HERE/f'{representation}_summary.csv',summaries)
            csv_write(HERE/f'{representation}_by_service.csv',services)
            csv_write(HERE/f'{representation}_pairs.csv',pairs)
        log('prefix_complete',representation=representation,packets=k,global_repeated_rows=len(positions),rows=n)
    temporal=[]
    for co,spec in cohorts.items():
        for r in temporal_overlap(gid,app,month,spec['codes'],names): temporal.append(dict(representation=representation,cohort=co,packets=30,reference_month='202501',**r))
    csv_write(HERE/f'{representation}_january_overlap.csv',temporal)
    save_json(HERE/f'{representation}_examples.json',examples)
    # For fixed denominators, adding packets cannot merge groups or increase conflicts.
    for co in cohorts:
        for period in ['ALL']+MONTHS:
            seq=[r for r in summaries if r['cohort']==co and r['period']==period and r['policy']=='padded']
            assert len(seq)==30
            assert all(a['rows']==b['rows'] and a['conflicting_rows']>=b['conflicting_rows'] and a['unique_patterns']<=b['unique_patterns'] for a,b in zip(seq,seq[1:]))
    save_json(done,dict(rows=n,summary_rows=len(summaries),service_rows=len(services),pair_rows=len(pairs),monotonicity_passed=True))


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--self-test',action='store_true'); parser.add_argument('--prepare-only',action='store_true'); args=parser.parse_args()
    self_test()
    if args.self_test:return
    manifest=prepare()
    log('source_prepared',rows=manifest['selected_valid_rows'],source_rows=manifest['source_rows'])
    if args.prepare_only:return
    for r in ['raw','clipped']:analyze_representation(manifest,r)
    log('complete',source_rows=manifest['source_rows'],selected_valid_rows=manifest['selected_valid_rows'])


if __name__=='__main__':main()
