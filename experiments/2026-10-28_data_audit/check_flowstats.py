"""Does adding full-record statistics resolve exact PPI30 collisions?

Only PPI30-repeated rows need extra inspection: appending fields cannot merge
different PPI keys. Native integer/float32 values are compared exactly; no
normalization, identifiers, absolute timestamps, domains, or IPs enter the key.
"""
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
import tables
from analyze import HERE, ROOT, SOURCE, grouped_statistics, csv_write, save_json


def duplicate_candidates(x, fingerprints=None):
    n=len(x)
    if fingerprints is None:
        fingerprints=np.empty(n,dtype='<u8')
        for start in range(0,n,100000):
            chunk=np.array(x[start:start+100000])
            fingerprints[start:start+len(chunk)]=np.fromiter(
                (int.from_bytes(hashlib.blake2b(row.tobytes(),digest_size=8).digest(),'little') for row in chunk),
                dtype='<u8',count=len(chunk))
            if start%1000000==0:print(json.dumps(dict(stage='sequential_fingerprint',rows_done=start+len(chunk),total=n)),flush=True)
    order=np.argsort(fingerprints,kind='stable')
    sorted_fp=fingerprints[order]
    equal=sorted_fp[1:]==sorted_fp[:-1]
    candidate=order[np.r_[equal,False]|np.r_[False,equal]]
    # Hashes ONLY shortlist rows; full original bytes define the actual groups.
    raw=np.array(x[candidate]).reshape(len(candidate),90).view('V360').ravel()
    _,groups=np.unique(raw,return_inverse=True)
    print(json.dumps(dict(stage='exact_candidates_grouped',candidates=len(candidate))),flush=True)
    return candidate,groups


def self_test():
    x=np.zeros((5,30,3),dtype='<i4');x[:,0,2]=[100,100,101,102,102]
    for fingerprints in [None,np.zeros(5,dtype='u8')]:
        # Deliberately force hash collisions. Full byte verification must split them.
        p,g=duplicate_candidates(x,fingerprints)
        s,_,_=grouped_statistics(g,np.array([1,2,1,1,1],dtype='u1')[p],[1,2],np.array([0,4,1]+[0]*61))
        assert s['rows']==5 and s['unique_patterns']==3 and s['conflicting_rows']==2
    print('PASS: candidate hashing and forced hash collisions verified against exact bytes',flush=True)


def main():
    self_test()
    m=json.loads((HERE/'manifest.json').read_text());n=m['selected_valid_rows']
    x=np.load(HERE/'ppi.npy',mmap_mode='r')[:n]
    meta=np.load(HERE/'meta.npy',mmap_mode='r')[:n]
    print('Sequential PPI30 fingerprint scan, followed by exact byte grouping',flush=True)
    positions,g=duplicate_candidates(x)
    # ID-sorted candidate records simplify a bounded sequential HDF5 read.
    sort_ids=np.argsort(meta['id'][positions]);positions=positions[sort_ids];g=g[sort_ids]
    cm=meta[positions];ids=cm['id']
    fields=[('DURATION','<f4'),('BYTES','<u8'),('BYTES_REV','<u8'),('PACKETS','<u4'),('PACKETS_REV','<u4')]
    hist=['PHIST_SRC_SIZES','PHIST_DST_SIZES','PHIST_SRC_IPT','PHIST_DST_IPT']
    stats=np.zeros(len(ids),dtype=np.dtype(fields+[(h,'<u4',(8,)) for h in hist]))
    filled=np.zeros(len(ids),dtype=bool)
    with tables.open_file(SOURCE,'r') as f:
        nodes=sorted(f.root.flows._f_iter_nodes(),key=lambda t:t.name)
        for di,t in enumerate(nodes):
            rows=t.read();pos=np.searchsorted(ids,rows['ID']);safe=np.minimum(pos,len(ids)-1)
            hit=(pos<len(ids))&(ids[safe]==rows['ID']);dst=pos[hit]
            assert not filled[dst].any()
            for name in stats.dtype.names:stats[name][dst]=rows[name][hit]
            filled[dst]=True
            if di%90==0:print(json.dumps(dict(day=t.name,filled=int(filled.sum()),candidates=len(ids))),flush=True)
    assert filled.all() and np.isfinite(stats['DURATION']).all() and (stats['DURATION']>=0).all()
    modes={
        'ppi30':[],
        'ppi30_counts4':['BYTES','BYTES_REV','PACKETS','PACKETS_REV'],
        'ppi30_flowstats5':[f[0] for f in fields],
        'ppi30_flowstats5_hist32':[f[0] for f in fields]+hist,
    }
    results=[];cohorts=m['cohorts']
    old={(r['cohort'],r['period'],r['policy']):r for r in csv.DictReader((HERE/'raw_summary.csv').open()) if r['packets']=='30'}
    supports={}
    for co,s in cohorts.items():
        for mi in [-1]+list(range(12)):
            for policy in ['padded','at_least_30']:
                mask=np.isin(meta['app'],s['codes'])
                if mi>=0:mask&=meta['month']==mi
                if policy=='at_least_30':mask&=meta['length']>=30
                supports[co,mi,policy]=np.bincount(meta['app'][mask],minlength=64)
    for mode,fs in modes.items():
        dtype=np.dtype([('ppi_group','<u8')]+[(name,stats.dtype.fields[name][0]) for name in fs])
        key=np.zeros(len(g),dtype=dtype);key['ppi_group']=g
        for name in fs:key[name]=stats[name]
        _,groups=np.unique(key.view(f'V{dtype.itemsize}').ravel(),return_inverse=True)
        for co,s in cohorts.items():
            for mi in [-1]+list(range(12)):
                period='ALL' if mi<0 else m['months'][mi]
                for policy in ['padded','at_least_30']:
                    mask=np.isin(cm['app'],s['codes'])
                    if mi>=0:mask&=cm['month']==mi
                    if policy=='at_least_30':mask&=cm['length']>=30
                    summary,_,_=grouped_statistics(groups[mask],cm['app'][mask],s['codes'],supports[co,mi,policy])
                    if mode=='ppi30':
                        previous=old[co,period,'padded' if policy=='padded' else 'at_least_k']
                        assert all(summary[k]==int(previous[k]) for k in ['rows','unique_patterns','same_label_duplicate_excess','conflicting_rows','conflicting_patterns','empirical_minimum_errors'])
                    r=dict(mode=mode,cohort=co,period=period,policy=policy,**summary);results.append(r)
                    if mi<0 and policy=='padded':print(json.dumps(r),flush=True)
    for co in cohorts:
        for period in ['ALL']+m['months']:
            for policy in ['padded','at_least_30']:
                rs=[r for r in results if r['cohort']==co and r['period']==period and r['policy']==policy]
                assert all(a['rows']==b['rows'] and a['unique_patterns']<=b['unique_patterns'] and a['conflicting_rows']>=b['conflicting_rows'] for a,b in zip(rs,rs[1:]))
    csv_write(HERE/'flowstats_collision_summary.csv',results)
    save_json(HERE/'flowstats_collision_check.json',dict(
        source_sha256=m['source_sha256'],selected_rows=n,ppi30_repeated_candidates=len(ids),
        features=modes,statistics_native_dtype=str(stats.dtype),
        scope='Same 12-month XS cohorts; full-record statistics, raw stored precision; no fitting or model feature scaling.',
        caveats=['These are exported flow records, not guaranteed complete application sessions.',
                 'Native DURATION float32 differences may reduce exact matches without improving separability.',
                 'Rounding, clipping, normalization or model quantization may introduce additional equality.',
                 'First 30 packet sequences plus full-record aggregates do not reconstruct all packet sequences.'],
        baseline_reproduced=True,monotonicity_passed=True,results=results))


if __name__=='__main__':main()
