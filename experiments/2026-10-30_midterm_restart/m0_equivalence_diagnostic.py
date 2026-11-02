import sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'experiments/2026-10-30_midterm_restart'))
from data import HERE,read_split
from models import statistics
import lightgbm as lgb,numpy as np
p=HERE/'main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M0_s201_n200';v=read_split('google_included20','validation');m=lgb.Booster(model_file=str(p/'best.txt'))
a=m.predict(statistics(v['X'])[0],num_threads=1)
with np.load(p/'validation_predictions.npz')as z:b=z['probabilities']
print('Validation',a.dtype,b.dtype,a.shape,b.shape,'maxabs',abs(a-b).max(),'argmaxdiff',np.count_nonzero(a.argmax(1)!=b.argmax(1)))
d=read_split('google_included20','evaluation_202504');a=m.predict(statistics(d['X'][:4096])[0],num_threads=1)
p=HERE/'main_recovered/evaluation_083e2ab53fa66d6f/extracted/main_evaluation/202504/M0_s201_n200/predictions.npz'
with np.load(p)as z:b=z['predicted_label'][:4096];lp=z['true_log_probability'][:4096]
c=np.log(np.clip(a[np.arange(4096),d['y'][:4096]],1e-30,1)).astype('f4')
print('April argmaxdiff',np.count_nonzero(a.argmax(1)!=b),'logpdiff',np.count_nonzero(c!=lp),'maxlogp',abs(c-lp).max())
