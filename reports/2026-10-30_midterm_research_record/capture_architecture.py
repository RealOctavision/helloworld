"""Documentation-only introspection; forward pass, no fitting or evaluation score."""
import sys, json, inspect, hashlib, shutil, importlib.metadata
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
EXP=ROOT/'experiments/2026-10-30_midterm_restart'
sys.path.insert(0,str(EXP))
import torch
import numpy as np
from models import make_model,statistics
from data import load_config,digest,read_split
out=HERE/'snapshots'
if (out/'architecture.json').exists():
    raise SystemExit('Snapshot already exists; preserve it and create a new version for a changed architecture.')
cfg=load_config(); torch.set_num_threads(2)
x=torch.tensor(read_split(cfg['primary_cohort'],'development_seed101',200)['X'][:2],dtype=torch.float32)
result={'captured_at':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),'purpose':'architecture introspection only, no fit/no validation or test score',
        'package_versions':{n:importlib.metadata.version(n) for n in ['torch','numpy','cesnet-models']},'models':{}}
sources={}
for kind in ['M1','M2','M3']:
    m=make_model(kind,20,101,cfg); m.eval(); trace=[]; hooks=[]
    def hook_for(name):
        def hook(mod,args,out):
            trace.append(dict(module=name,type=type(mod).__name__,input_shapes=[list(t.shape) for t in args if isinstance(t,torch.Tensor)],output_shape=list(out.shape) if isinstance(out,torch.Tensor) else None))
        return hook
    for n,mod in m.named_modules():
        if n in ['backbone.packet_size_nn_embedding','backbone.packet_ipt_nn_embedding','backbone.cnn_ppi','backbone.cnn_ppi_global_pool','head'] or n.startswith('backbone.cnn_ppi.') and n.count('.')==2 or n.startswith('blocks.'):
            hooks.append(mod.register_forward_hook(hook_for(n)))
    with torch.inference_mode(): y=m(x)
    for h in hooks: h.remove()
    modules=[dict(name=n,type=type(mod).__name__,parameters_direct=sum(p.numel() for p in mod.parameters(recurse=False)),description=str(mod)) for n,mod in m.named_modules() if not list(mod.children())]
    details=dict(parameters=sum(p.numel() for p in m.parameters()),trainable_parameters=sum(p.numel() for p in m.parameters() if p.requires_grad),output_shape=list(y.shape),modules=modules,forward_trace=trace,repr=str(m))
    if kind in ['M1','M2']:
        b=m.backbone
        details['ipt_bins']=b.ipt_bins.tolist()
        details['initial_gem_p']=float(b.cnn_ppi_global_pool[0].p.detach())
        details['freeze_bn_running_stats']=m.freeze_bn_statistics
        details['package_source_path']=inspect.getfile(type(b))
        sources['official_multimodal_cesnet_enhanced.py']=Path(inspect.getfile(type(b)))
        sources['official_pooling.py']=Path(inspect.getfile(type(b.cnn_ppi_global_pool[0])))
    result['models'][kind]=details
import cesnet_models.models as official_models
sources['official_model_factory.py']=Path(inspect.getfile(official_models))
for name in ['config.json','models.py','training.py','data.py','colab_development.py']:
    sources[name]=EXP/name
sources['restart_decisions_at_capture.md']=ROOT/'experiments/2026-10-28_data_audit/restart_decisions.md'
sources['model_structure_review_at_capture.md']=ROOT/'experiments/2026-10-28_data_audit/model_structure_review.md'
sources['original_plan_text.txt']=ROOT/'reports/2026-10-26_planned_experiments/plan_source.txt'
sources['settings_explanation_user_supplied.txt']=ROOT/'experiments/2026-10-28_data_audit/settings_explanation_user_supplied_2026-10-30.txt'
for name,source in sources.items(): shutil.copy2(source,out/name)
result['m0_feature_order']=statistics(x.numpy())[1]
(out/'architecture.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(out/'source_hashes.json').write_text(json.dumps({name:dict(source=str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else str(source),sha256=digest(out/name)) for name,source in sources.items()},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:{'parameters':v['parameters'],'initial_gem_p':v.get('initial_gem_p'),'trace':v['forward_trace']} for k,v in result['models'].items()},indent=2))
