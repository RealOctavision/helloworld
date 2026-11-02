"""Bounded real-data check, NOT hyperparameter selection or final performance."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import resource
import time
import traceback

import numpy as np
import torch

from data import HERE, ROOT, load_config, read_split, exact_keys, contains, canonical, write_json, digest
from models import make_model, state_digest, statistics, kd_loss
from training import (fit_network, fit_m0, checked_step, schedule, save_checkpoint,
                      load_checkpoint, validate_teacher_meta, score_groups, logits_for)


def resume_probe(train, cfg, output):
    """Compare uninterrupted vs resumed NEXT UPDATE, including dropout and BN."""
    torch.set_num_threads(cfg['training']['cpu_threads'])
    torch.use_deterministic_algorithms(True)
    device = torch.device('cpu')
    model = make_model('M1', 20, 999, cfg)
    opt = torch.optim.AdamW(model.parameters(), lr=0.0003, weight_decay=0.0001)
    sched = schedule(opt, 2, 2, 1)
    x = torch.as_tensor(train['X'][:32], dtype=torch.float32)
    y = torch.as_tensor(train['y'][:32], dtype=torch.long)
    checked_step(model, opt, sched, x, y, None, 0, 1)
    path = output/'resume_probe.pt'
    save_checkpoint(path, model, opt, sched, {'purpose':'nonperformance_resume_test'}, 0, [], device)
    loss = checked_step(model, opt, sched, x, y, None, 0, 1)
    expected_hash = state_digest(model)
    replacement = make_model('M1', 20, 999, cfg)
    replacement_opt = torch.optim.AdamW(replacement.parameters(), lr=0.0003, weight_decay=0.0001)
    replacement_sched = schedule(replacement_opt, 2, 2, 1)
    load_checkpoint(path, replacement, replacement_opt, replacement_sched, device)
    resumed_loss = checked_step(replacement, replacement_opt, replacement_sched, x, y, None, 0, 1)
    if resumed_loss != loss or state_digest(replacement) != expected_hash:
        raise AssertionError('Saved RNG/optimizer/scheduler did not exactly reproduce next update')
    return dict(next_loss_exact=True, next_model_state_exact=True, includes_dropout_bn_optimizer_scheduler=True)


def functional_probes(cfg, train):
    # Exercise class-count variants without fitting extra models.
    for classes in [13,20]:
        for kind in ['M1','M2','M3']:
            model = make_model(kind, classes, 5, cfg, load_pretrained=False).eval()
            with torch.inference_mode():
                assert model(torch.as_tensor(train['X'][:2], dtype=torch.float32)).shape == (2,classes)
    # Gradients at alpha=0 must be identical to plain CE.
    z = torch.randn(8,20,requires_grad=True)
    y = torch.arange(8)
    a = kd_loss(z,y,None,0,2)
    b = kd_loss(z,y,torch.randn_like(z),0,4)
    ga, = torch.autograd.grad(a,z,retain_graph=True)
    gb, = torch.autograd.grad(b,z)
    assert torch.equal(ga,gb)
    # Wrong label budget / output ordering / source IDs must be rejected.
    for field, value in [('budget',1000),('classes',['wrong']),('train_ids_sha256','wrong')]:
        meta = dict(budget=50, classes=['a','b'], train_ids_sha256='correct')
        try:
            validate_teacher_meta(meta,{field:value})
        except ValueError:
            pass
        else:
            raise AssertionError('Mismatched teacher accepted')
    # DIR ablation cannot erase the valid-packet mask.
    model = make_model('M3',20,5,cfg,drop_channel=1)
    x = torch.as_tensor(train['X'][:8],dtype=torch.float32)
    assert torch.isfinite(model(x)).all()
    # Empty subgroup remains N/A, absent classes remain in fixed-class macro F1.
    result = score_groups(np.array([0]),np.array([[1.,0.]]),2,np.array([True]),np.array([False]))
    assert result['train_nonoverlap']['macro_f1'] is None
    assert result['all']['macro_f1'] == 0.5
    return dict(class_counts=[13,20], alpha_zero_gradients_equal_ce=True,
                teacher_mismatch_rejected=True, dir_ablation_mask_preserved=True,
                empty_group_na=True, fixed_class_macro_f1=True)


def bench(fn, samples=100):
    for i in range(10):
        fn(i)
    durations=[]
    for i in range(samples):
        t=time.perf_counter_ns();fn(i);durations.append((time.perf_counter_ns()-t)/1e6)
    return dict(n=samples, median_ms=float(np.median(durations)), p95_ms=float(np.percentile(durations,95)))


@torch.inference_mode()
def benchmark_network(model, x):
    torch.set_num_threads(1)
    model=model.cpu().eval()
    prepared=torch.as_tensor(x[:128],dtype=torch.float32)
    result=dict(batch1_model_including_internal_transform=bench(lambda i:model(prepared[i%len(prepared):i%len(prepared)+1])),
                batch1_common_preprocessing_and_model=bench(lambda i:model(torch.as_tensor(canonical(x[i%len(x):i%len(x)+1]),dtype=torch.float32))))
    for _ in range(5):model(prepared)
    t=time.perf_counter()
    for _ in range(20):model(prepared)
    result['batch128_flows_per_second']=20*len(prepared)/(time.perf_counter()-t)
    result['threads']=1
    result['observation_wait_included']=False
    return result


def run(output):
    cfg=load_config();sc=cfg['smoke'];cohort=sc['cohort']
    train=read_split(cohort,f"development_seed{sc['seed']}",sc['budget'])
    val=read_split(cohort,'validation')
    mask=val['rank']<sc['validation_per_class']
    val={k:v[mask] for k,v in val.items()}
    output.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    report=dict(status='running',purpose='pipeline_smoke_not_performance',
                config_sha256=digest(HERE/'config.json'),device='cpu',platform=platform.platform(),
                versions={p:importlib.metadata.version(p) for p in ['torch','numpy','cesnet-models','lightgbm']},
                train_rows=len(train['id']),validation_rows=len(val['id']),
                April_May_scores_computed=False,models={})
    write_json(output/'summary.json',report)
    try:
        report['functional_probes']=functional_probes(cfg,train)
        report['resume_probe']=resume_probe(train,cfg,output)
        m0,r0=fit_m0(train,val,cfg,output/'M0',sc['seed'],max_rounds=sc['m0_max_boost_rounds'],patience=sc['m0_patience'])
        r0['performance_result']=False
        features,_=statistics(val['X'])
        r0['cpu_benchmark']=dict(threads=1,
            batch1_model=bench(lambda i:m0.predict(features[i%len(features):i%len(features)+1],num_threads=1)),
            batch1_common_preprocessing_features_and_model=bench(lambda i:m0.predict(statistics(canonical(val['X'][i%len(val['X']):i%len(val['X'])+1]))[0],num_threads=1)))
        write_json(output/'M0'/'metrics.json',r0)
        report['models']['M0']={k:v for k,v in r0.items() if k not in ['history','validation']}
        for kind in ['M1','M2','M3','M4','M5']:
            teacher=None
            if kind=='M4':teacher=output/'M1'/'best.pt'
            if kind=='M5':teacher=output/'M2'/'best.pt'
            group=kind if kind in ['M1','M2'] else 'student'
            model,result=fit_network(kind,train,val,cfg,output/kind,cohort,sc['seed'],sc['budget'],
                cfg['training']['lr_candidates'][group][1],sc['epochs'],
                teacher_checkpoint=teacher,alpha=0.25 if teacher else 0.0,temperature=2.0,
                phase='smoke',warmup_epochs=sc['warmup_epochs'],time_limit=sc['time_limit_seconds_per_model'])
            result['cpu_benchmark']=benchmark_network(model,val['X'])
            predictions=logits_for(model,val['X'],torch.device('cpu')).softmax(1).numpy()
            overlap=contains(exact_keys(val['X']),exact_keys(train['X']))
            # Validation records themselves cannot be unseen to validation.
            result['validation_grouping_probe']=score_groups(val['y'],predictions,len(cfg['cohorts'][cohort]['classes']),overlap,np.zeros(len(val['y']),dtype=bool))
            write_json(output/kind/'metrics.json',result)
            report['models'][kind]={k:v for k,v in result.items() if k not in ['history','validation','validation_grouping_probe']}
            write_json(output/'summary.json',report)
            del model
        student_hashes={report['models'][k]['initial_state_sha256'] for k in ['M3','M4','M5']}
        assert len(student_hashes)==1,'Student initial states differ'
        assert len({report['models'][k]['train_ids_sha256'] for k in report['models']})==1
        assert digest(ROOT/cfg['pretrained_checkpoint'])==cfg['pretrained_sha256']
        report['student_initial_states_identical']=True
        report['all_six_models_training_ids_identical']=True
        report['public_checkpoint_unchanged']=True
        report['status']='passed'
        report['elapsed_seconds']=time.perf_counter()-started
        report['process_peak_rss_bytes']=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*(1 if platform.system()=='Darwin' else 1024)
        report['memory_note']='Peak for the entire smoke process; not isolated per-model memory.'
        write_json(output/'summary.json',report)
        print(json.dumps(dict(status='passed',output=str(output),elapsed_seconds=report['elapsed_seconds'])),flush=True)
    except Exception:
        report.update(status='failed',failure=traceback.format_exc(),elapsed_seconds=time.perf_counter()-started)
        write_json(output/'summary.json',report)
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output',default='smoke')
    args=p.parse_args()
    run(HERE/args.output)
