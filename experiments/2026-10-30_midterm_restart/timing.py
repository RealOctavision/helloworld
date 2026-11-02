"""CPU planning estimate from smoke training and full-February forward timing.
No April/May predictions, no extra fitting, and no inferred T4 measurements.
"""
import argparse
import json
import math
import time
import numpy as np
import torch
from data import HERE, load_config, read_split, write_json
from models import make_model
from training import load_checkpoint, logits_for


def run(smoke_dir):
    cfg=load_config()
    cohort=cfg['primary_cohort']
    val=read_split(cohort,'validation')
    torch.set_num_threads(cfg['training']['cpu_threads'])
    seconds={}
    raw={}
    for kind in ['M1','M2','M3']:
        model=make_model(kind,20,cfg['smoke']['seed'],cfg,load_pretrained=False)
        load_checkpoint(smoke_dir/kind/'best.pt',model)
        logits_for(model,val['X'][:128],torch.device('cpu'))
        t=time.perf_counter()
        logits=logits_for(model,val['X'],torch.device('cpu'))
        seconds[kind]=time.perf_counter()-t
        assert logits.shape==(len(val['id']),20)
        # Deliberately discard logits; this is timing, not setting selection.
        del logits,model
        print(kind,'full validation forward seconds',round(seconds[kind],3),flush=True)
    for kind in ['M1','M2','M3','M4','M5']:
        r=json.loads((smoke_dir/kind/'metrics.json').read_text())
        raw[kind]=sum(h['fitting_seconds'] for h in r['history'])/(len(r['history'])*r['steps_per_epoch'])
    epochs=cfg['training']['candidate_epochs']; batch=cfg['training']['batch_size']
    estimates={}
    for budget in cfg['budgets']:
        steps=math.ceil(20*budget/batch)*epochs
        values={}
        for kind in raw:
            group=kind if kind in ['M1','M2'] else 'M3'
            values[kind]=raw[kind]*steps + seconds[group]*(epochs+1)
            if kind in ['M4','M5']:
                teacher='M1' if kind=='M4' else 'M2'
                values[kind]+=seconds[teacher]*20*budget/len(val['id'])
        estimates[str(budget)]={'per_model_seconds':values,
            'five_repeats_neural_seconds':sum(values.values())*5}
    dev=estimates['200']['per_model_seconds']
    report=dict(device='local CPU only',threads=cfg['training']['cpu_threads'],
        full_validation_rows=len(val['id']),full_validation_forward_seconds=seconds,
        measured_train_seconds_per_update=raw,assumed_epochs=epochs,epochs_frozen=False,
        primary_cohort_estimates=estimates,
        development_neural_seconds=2*(3*dev['M1']+3*dev['M2']+3*dev['M3']+9*dev['M4']+9*dev['M5']),
        all_four_budgets_main_neural_seconds=sum(e['five_repeats_neural_seconds'] for e in estimates.values()),
        T4_estimate=None,T4_reason='No GPU allocated or measured in this preparation task',
        exclusions=['LightGBM fitting','April/May final inference','transfer/setup time','long-run thermal effects','additional development epoch changes'],
        interpretation='Linear planning approximation from a short CPU run; not a runtime guarantee or a GPU forecast. Teacher-logit caching can reduce repeated KD cost.')
    write_json(HERE/'timing_estimate.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--smoke-dir',default='smoke_v2');a=p.parse_args()
    run(HERE/a.smoke_dir)
