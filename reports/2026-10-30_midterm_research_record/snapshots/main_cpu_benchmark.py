"""One fresh CPU process per final model; never fits or tunes a model."""
import argparse
import gc
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
import numpy as np
import torch
from data import HERE,digest,read_split,write_json
from models import make_model,statistics
from training import load_checkpoint,hash_bytes
from colab_main import frozen_config

def rss():
    return int(subprocess.run(['ps','-o','rss=','-p',str(os.getpid())],capture_output=True,text=True,check=True).stdout.strip())*1024

def measure(fn,n,cycle=None):
    values=[]
    for i in range(n):
        t=time.perf_counter_ns()
        if cycle is None:fn()
        else:fn(i%cycle)
        values.append((time.perf_counter_ns()-t)/1e6)
    a=np.asarray(values)
    return dict(iterations=n,median_ms=float(np.median(a)),p95_ms=float(np.percentile(a,95)),
                mean_ms=float(a.mean()),min_ms=float(a.min()),raw_ms=values)

def worker(archive_root,output,kind,seed):
    cfg,f=frozen_config();cfg['training']['cpu_threads']=1
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    name=f'{kind}_s{seed}_n200';fit=archive_root/'main_training/fits'/name
    cp=fit/('best.txt' if kind=='M0' else 'best.pt')
    frozen=json.loads((archive_root/'main_training/frozen_checkpoints.json').read_text())
    assert digest(cp)==frozen['checkpoints'][name]
    val=read_split(f['cohort'],'validation')
    rng=np.random.default_rng(20261030)
    indices=np.concatenate([rng.permutation(np.flatnonzero(val['y']==label))[:6+int(label<8)] for label in range(20)])
    indices=rng.permutation(indices);x=val['X'][indices]
    assert len(indices)==128 and len(np.unique(val['y'][indices]))==20
    xt=torch.as_tensor(x,dtype=torch.float32)
    gc.collect();baseline=rss()
    target=output/name;target.mkdir(parents=True,exist_ok=True)
    if kind=='M0':
        import lightgbm as lgb
        model=lgb.Booster(model_file=str(cp));features=statistics(x)[0]
        infer1=lambda i:model.predict(features[i:i+1],num_threads=1)
        extract1=lambda i:statistics(x[i:i+1])[0]
        total1=lambda i:model.predict(statistics(x[i:i+1])[0],num_threads=1)
        inferbatch=lambda:model.predict(features,num_threads=1)
        totalbatch=lambda:model.predict(statistics(x)[0],num_threads=1)
        parameters=None;inference_file=cp
    else:
        model=make_model(kind,20,seed,cfg,load_pretrained=False);payload=load_checkpoint(cp,model);model.eval()
        assert payload['meta']['phase']=='main' and payload['meta']['seed']==seed
        del payload
        infer1=lambda i:model(xt[i:i+1]);inferbatch=lambda:model(xt)
        total1=infer1;totalbatch=inferbatch;extract1=None
        parameters=sum(p.numel() for p in model.parameters())
        inference_file=target/'inference_weights.pt'
        torch.save(dict(model=model.state_dict(),kind=kind,seed=seed,frozen_settings_sha256=digest(HERE/'main_frozen.json')),inference_file)
    gc.collect();loaded=rss()
    conf=f['local_cpu_benchmark']
    with torch.inference_mode():
        for i in range(conf['batch1_warmup']):total1(i%128)
        warm=rss()
        batch1=measure(total1,conf['batch1_iterations'],cycle=128)
        forward_only=measure(infer1,conf['batch1_iterations'],cycle=128) if kind=='M0' else batch1
        extraction=measure(extract1,conf['batch1_iterations'],cycle=128) if extract1 else None
        for _ in range(conf['throughput_warmup']):totalbatch()
        throughput=measure(totalbatch,conf['throughput_iterations'])
        throughput['flows_per_second']=128/(throughput['mean_ms']/1000)
    peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_bytes=int(peak if sys.platform=='darwin' else peak*1024)
    result=dict(model=kind,seed=seed,checkpoint_sha256=digest(cp),frozen_settings_sha256=digest(HERE/'main_frozen.json'),
                benchmark_source_sha256=digest(Path(__file__)),input_ids_sha256=hash_bytes(val['id'][indices]),
                input_class_counts=np.bincount(val['y'][indices],minlength=20).tolist(),
                threads=1,precision='FP32',batch1=batch1,batch1_forward_only=forward_only,m0_extraction=extraction,
                batch128=throughput,parameters=parameters,inference_file_bytes=inference_file.stat().st_size,
                inference_file=str(inference_file),checkpoint_with_optimizer_bytes=cp.stat().st_size,
                memory=dict(baseline_rss_bytes=baseline,loaded_rss_bytes=loaded,warmed_rss_bytes=warm,
                            loaded_minus_baseline_bytes=loaded-baseline,process_peak_rss_bytes=peak_bytes,
                            note='Fresh process for each model. RSS and process peak include runtime/import/allocator; delta is not intrinsic model memory.'),
                timing_scope='Input already canonical and resident; NN internal fixed transforms/embedding included. M0 primary timing includes 16-statistic extraction. Packet waiting, capture, disk I/O and array-to-tensor preparation excluded.',
                environment=dict(platform=platform.platform(),machine=platform.machine(),python=platform.python_version(),
                cpu=subprocess.run(['sysctl','-n','machdep.cpu.brand_string'],capture_output=True,text=True).stdout.strip() if sys.platform=='darwin' else platform.processor(),
                packages={p:importlib.metadata.version(p) for p in ['torch','numpy','cesnet-models','lightgbm']}))
    write_json(target/'benchmark.json',result);print(name,'CPU batch1 median',batch1['median_ms'],flush=True)

def run(root,output):
    cfg,f=frozen_config();output.mkdir(parents=True,exist_ok=True)
    for seed in f['seeds']:
        for kind in ['M0','M1','M2','M3','M4','M5']:
            p=output/f'{kind}_s{seed}_n200/benchmark.json'
            if p.exists():
                r=json.loads(p.read_text());cp=root/'main_training/fits'/f'{kind}_s{seed}_n200'/('best.txt' if kind=='M0' else 'best.pt')
                if r['checkpoint_sha256']!=digest(cp) or r['frozen_settings_sha256']!=digest(HERE/'main_frozen.json'):raise ValueError('Benchmark reuse mismatch')
                continue
            subprocess.run([sys.executable,str(Path(__file__).resolve()),'--root',str(root),'--output',str(output),'--worker',kind,'--seed',str(seed)],check=True)
            write_json(output/'status.json',dict(state='running',completed=len(list(output.glob('*/benchmark.json'))),planned=30))
    write_json(output/'status.json',dict(state='completed',completed=30,planned=30))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,default=HERE/'main_cpu_benchmark')
    p.add_argument('--worker',choices=['M0','M1','M2','M3','M4','M5']);p.add_argument('--seed',type=int);a=p.parse_args()
    if a.worker:worker(a.root.resolve(),a.output.resolve(),a.worker,a.seed)
    else:run(a.root.resolve(),a.output.resolve())
