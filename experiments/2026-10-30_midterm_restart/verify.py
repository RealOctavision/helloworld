"""Focused manifest and artifact checks, with independent byte-set witnesses."""
import json
from pathlib import Path
import numpy as np
import torch
from data import HERE, load_config, read_split, exact_keys, contains, digest, write_json
from training import score_groups


def run():
    cfg=load_config()
    manifest=json.loads((HERE/'prepared/manifest.json').read_text())
    assert digest(HERE/'config.json')==manifest['config_sha256']
    for name,sha in manifest['artifacts'].items():
        assert digest(HERE/'prepared'/name)==sha,name
    result={'status':'passed','cohorts':{},'evaluated_test_performance':False}
    for cohort,spec in cfg['cohorts'].items():
        c=len(spec['classes'])
        validation=read_split(cohort,'validation')
        union=set(k.tobytes() for k in exact_keys(validation['X']))
        val_ids=set(validation['id'].tolist())
        runs={}
        for phase,seeds,max_n in [('development',cfg['development_seeds'],200),('main',cfg['main_seeds'],1000)]:
            for seed in seeds:
                a=read_split(cohort,f'{phase}_seed{seed}')
                keys=exact_keys(a['X'])
                assert len(np.unique(keys))==len(keys)
                assert len(np.unique(a['id']))==len(a['id'])
                assert not val_ids.intersection(a['id'].tolist())
                assert np.all(a['day']//100==202501)
                assert np.array_equal(np.bincount(a['y'],minlength=c),np.full(c,max_n))
                union.update(k.tobytes() for k in keys)
                if phase=='main':
                    runs[seed]=(a,keys)
                    previous=set()
                    for budget in cfg['budgets']:
                        selected=a['rank']<budget
                        ids=set(a['id'][selected].tolist())
                        assert previous<=ids and len(ids)==c*budget
                        previous=ids
        for month in cfg['months']['evaluation']:
            a=read_split(cohort,'evaluation_'+month)
            with np.load(HERE/'prepared'/cohort/f'evaluation_groups_{month}.npz',allow_pickle=False) as f:
                masks=dict(f)
            assert np.array_equal(a['id'],masks['id'])
            assert np.all(a['day']//100==int(month))
            ii=np.random.default_rng(917).choice(len(a['id']),min(256,len(a['id'])),replace=False)
            # Oracle uses Python full-byte sets rather than builder searchsorted.
            witnesses=[x.tobytes() for x in exact_keys(a['X'][ii])]
            assert np.array_equal(masks['common_unseen'][ii],[x not in union for x in witnesses])
            for seed,(train,keys) in runs.items():
                for budget in cfg['budgets']:
                    reference=set(k.tobytes() for k in keys[train['rank']<budget])
                    mask=masks[f'seed{seed}_n{budget}_train_overlap']
                    assert np.array_equal(mask[ii],[x in reference for x in witnesses])
                    assert not np.any(mask & masks['common_unseen'])
        result['cohorts'][cohort]={'nested_budgets':True,'balanced_unique_training':True,
            'source_id_disjoint':True,'grouping_witnesses_per_month':256,
            'overlap_definitions_checked_for_main_seed_budget_pairs':20}
        print(cohort,'prepared data checks passed',flush=True)
    # Validation can never be Common-unseen because validation is excluded by definition.
    sc=cfg['smoke'];train=read_split(sc['cohort'],f"development_seed{sc['seed']}",sc['budget'])
    val=read_split(sc['cohort'],'validation');m=val['rank']<sc['validation_per_class']
    val={k:v[m] for k,v in val.items()}
    overlap=contains(exact_keys(val['X']),exact_keys(train['X']))
    prior=HERE/'verification.json'
    annotation_corrections=json.loads(prior.read_text()).get('validation_annotation_pre_correction_sha256',{}) if prior.exists() else {}
    for kind in ['M1','M2','M3','M4','M5']:
        folder=HERE/'smoke_v2'/kind;path=folder/'metrics.json'
        r=json.loads(path.read_text())
        assert digest(folder/'best.pt')==r['best_checkpoint_sha256']
        assert digest(folder/'last.pt')==r['last_checkpoint_sha256']
        with np.load(folder/'validation_predictions.npz',allow_pickle=False) as f:
            assert np.array_equal(f['id'],val['id'])
            assert np.isfinite(f['probabilities']).all()
            assert np.allclose(f['probabilities'].sum(1),1)
            corrected=score_groups(val['y'],f['probabilities'],20,overlap,np.zeros(len(val['y']),dtype=bool))
        assert r['validation_grouping_probe']==corrected,'Incorrect validation grouping annotation'
    s=json.loads((HERE/'smoke_v2/summary.json').read_text())
    assert s['status']=='passed' and s['student_initial_states_identical']
    assert s['all_six_models_training_ids_identical'] and s['resume_probe']['next_model_state_exact']
    assert s['models']['M1']['bn_statistics_unchanged'] is False
    assert s['models']['M2']['bn_statistics_unchanged'] is True
    result['smoke_summary_sha256']=digest(HERE/'smoke_v2/summary.json')
    result['original_hdf5_spot_check']=json.loads((HERE/'cache_source_check.json').read_text())['status']
    result['validation_annotation_pre_correction_sha256']=annotation_corrections
    result['scope']='Prepared data and short CPU pipeline; no campaign accuracy, GPU timing, or isolated per-model memory claim.'
    result['code_sha256']={p.name:digest(p) for p in HERE.glob('*.py')}
    write_json(HERE/'verification.json',result)


if __name__=='__main__':run()
