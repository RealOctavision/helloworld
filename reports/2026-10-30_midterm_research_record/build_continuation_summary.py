"""Publish only verified continuation results, with missing stages explicit. No fitting."""
from pathlib import Path
from datetime import datetime,timezone
import json,statistics as st,hashlib
import numpy as np
H=Path(__file__).resolve().parent;R=H.parents[1];E=R/'experiments/2026-10-30_midterm_restart'
MODELS=['M0','M1','M2','M3','M4','M5'];SEEDS=[201,202,203,204,205]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def readreg(base,name):
 p=base/(name+'_registry.json')
 if not p.exists():return None
 d=json.loads((R/json.loads(p.read_text())['verification']).read_text())
 if not d.get('verified'):raise ValueError('Unverified registry')
 return d
def table(h,rows):return '\n|'+'|'.join(h)+'|\n|'+'|'.join(['---']*len(h))+'|\n'+''.join('|'+'|'.join(map(str,r))+'|\n'for r in rows)+'\n'
def avg(v,scale=1):
 if not v or any(x is None for x in v):return 'N/A'
 a=[float(x)*scale for x in v];return f'{st.mean(a):.3f} ± {st.stdev(a):.3f}'
def cpu_check(base,training,stage,conf):
 records=[];lookup={(r['model'],r['seed']):r for r in training['records']}
 source=E/('main_cpu_benchmark.py'if stage=='mixed_n200'else'continuation_cpu_benchmark.py')
 for p in sorted(base.glob('*/benchmark.json')):
  r=json.loads(p.read_text());q=lookup[(r['model'],r['seed'])]
  if r['checkpoint_sha256']!=q['checkpoint_sha256'] or r['threads']!=1 or r['precision']!='FP32' or r['benchmark_source_sha256']!=sha(source):raise ValueError('CPU provenance')
  if sum(r['input_class_counts'])!=128 or min(r['input_class_counts'])<=0:raise ValueError('CPU inputs')
  for key,count in [('batch1',conf['batch1_iterations']),('batch128',conf['throughput_iterations'])]:
   m=r[key];v=np.asarray(m['raw_ms'])
   if len(v)!=count or not np.isfinite(v).all() or np.any(v<0):raise ValueError('CPU repetitions')
   for k,value in [('median_ms',np.median(v)),('p95_ms',np.percentile(v,95)),('mean_ms',v.mean())]:
    if not np.isclose(value,m[k],atol=1e-12,rtol=1e-12):raise ValueError('CPU aggregate')
  if not np.isclose(r['batch128']['flows_per_second'],128000/r['batch128']['mean_ms']):raise ValueError('CPU throughput')
  records.append(r)
 if records and (len({r['input_ids_sha256']for r in records})!=1 or len({(r['model'],r['seed'])for r in records})!=len(records)):raise ValueError('CPU coverage')
 return records

def run():
 plan=json.loads((E/'continuation_frozen.json').read_text());basef=json.loads((E/'main_frozen.json').read_text())
 stages=[dict(id='mixed_n200',cohort='google_included20',budget=200),*plan['stages']]
 summary=dict(generated_utc=datetime.now(timezone.utc).isoformat(),stages=[],rows=[],paired=[],class_rows=[],confusions=[],cpu_rows=[],source_registries=[],complete=False)
 md='## 후속 결과 — 라벨 수·서비스 구성·CPU 비용\n\n이 절의 수치는 로컬 회수·검증을 통과한 원본에서만 계산한다. 개발60fit·대표30fit·후속150fit은 서로 다른 실행이며, 소실된 미회수 시도를 완료 수에 더하지 않는다. ±는seed201~205의표본SD(ddof=1)이고신뢰구간이아니다.\n\n'
 coverage=[]
 for stage in stages:
  sid=stage['id'];root=E/'main_recovered'if sid=='mixed_n200'else E/'continuation_recovered'/sid
  tr=readreg(root,'training');ev=readreg(root,'evaluation');local=None if sid=='mixed_n200'else readreg(root,'local_m0')
  fits=tr['completed']if tr else 0
  records=(ev['records']if ev else [])+(local['records']if local else [])
  bench=cpu_check(E/'main_cpu_benchmark'if sid=='mixed_n200'else root/'cpu_benchmark',tr,sid,basef['local_cpu_benchmark'])if tr else []
  coverage.append([sid,stage['cohort'],stage['budget'],f'{fits}/30',f'{len(records)}/60',f'{len(bench)}/30'])
  summary['stages'].append(dict(**stage,fits=fits,evaluations=len(records),cpu=len(bench)))
  for name in ['training','evaluation','local_m0']:
   p=root/(name+'_registry.json')
   if p.exists():summary['source_registries'].append(dict(path=str(p.relative_to(R)),sha256=sha(p)))
  if tr:
   md+=f'<details><summary>{sid} 학습곡선·2월선택·시간</summary>\n\n'
   train_rows=[]
   for r in tr['records']:
    source=R/r['metrics_path'];raw=json.loads(source.read_text());hist=raw.get('history',[]);last=hist[-1] if hist else {}
    train_rows.append([r['run'],f"{100*r['validation']['macro_f1']:.3f}",r['selected_step'],r['completed_steps'],
      f"{100*last['validation']['macro_f1']:.3f}"if last else 'N/A',f"{r['resources']['full_fit_seconds']:.2f}",
      f"[전체epoch와설정](../../{source.relative_to(R)})"])
   md+=table(['run','선택F1(%)','선택epoch/round','완료epoch/round','마지막F1(%)','전체fit초','원본곡선'],train_rows)
   md+='2월checkpoint선택값이며4·5월성능과구분한다. 마지막epoch선택만으로수렴을단정하지않고공통cosine일정과라벨별update수를함께해석한다. fit시간에는모델초기화·교사예측·학습·검증·checkpoint저장이포함된다.\n\n</details>\n'
  if len(records)!=60:continue
  by={(r['month'],r['model'],r['seed']):r for r in records}
  if len(by)!=60:raise ValueError('Duplicate month/model/seed')
  classes=records[0]['classes'];C=len(classes)
  for month in ['202504','202505']:
   for group in ['all','train_overlap','train_nonoverlap','common_unseen']:
    for model in MODELS:
     rr=[by[month,model,s]['groups'][group]for s in SEEDS];n=[r['n']for r in rr]
     item=dict(stage=sid,cohort=stage['cohort'],budget=stage['budget'],classes=C,month=month,group=group,model=model,n=n,classes_with_support=[r['classes_with_support']for r in rr])
     for key in ['macro_f1','accuracy','gt_cross_entropy']:
      vals=[r[key] for r in rr];item[key]=dict(per_seed=vals,mean=st.mean(vals)if all(n)else None,sd=st.stdev(vals)if all(n)else None)
     summary['rows'].append(item)
   for a,b in [('M2','M1'),('M4','M3'),('M5','M3'),('M5','M4'),('M2','M5')]:
    values=[100*(by[month,a,s]['groups']['all']['macro_f1']-by[month,b,s]['groups']['all']['macro_f1'])for s in SEEDS]
    summary['paired'].append(dict(stage=sid,month=month,comparison=a+'−'+b,per_seed_pp=values,mean_pp=st.mean(values),sd_pp=st.stdev(values),positive_seeds=sum(v>0 for v in values)))
   for i,c in enumerate(classes):
    summary['class_rows'].append(dict(stage=sid,month=month,service=c,support=by[month,'M0',SEEDS[0]]['groups']['all']['support'][i],
     models={m:{key:st.mean(by[month,m,s]['groups']['all'][key][i]for s in SEEDS)for key in ['per_class_f1','per_class_precision','per_class_recall']}for m in MODELS}))
   for m in ['M2','M5']:
    matrix=np.sum([by[month,m,s]['groups']['all']['confusion']for s in SEEDS],axis=0);pairs=[]
    for i in range(C):
     for j in range(C):
      if i!=j and matrix[i,j]:pairs.append((int(matrix[i,j]),i,j))
    summary['confusions'].append(dict(stage=sid,month=month,model=m,scope='Sum of five model confusion matrices on the same evaluation flows; not five independent datasets',pairs=[dict(true=classes[i],predicted=classes[j],count=n)for n,i,j in sorted(pairs,reverse=True)[:10]]))
  for m in MODELS:
   rr=[r for r in bench if r['model']==m]
   if len(rr)!=5:continue
   summary['cpu_rows'].append(dict(stage=sid,model=m,parameters=rr[0]['parameters'],checkpoint_sha256=[r['checkpoint_sha256']for r in rr],
    **{key:dict(per_seed=v,mean=st.mean(v),sd=st.stdev(v))for key,v in {
      'batch1_median_ms':[r['batch1']['median_ms']for r in rr], 'batch1_p95_ms':[r['batch1']['p95_ms']for r in rr],
      'batch128_flows_s':[r['batch128']['flows_per_second']for r in rr], 'inference_MiB':[r['inference_file_bytes']/2**20 for r in rr],
      'warm_RSS_MiB':[r['memory']['warmed_rss_bytes']/2**20 for r in rr]}.items()}))
 md+=table(['조건','서비스구성','클래스당표본','학습','월별평가','CPU모델측정'],coverage)
 for month in ['202504','202505']:
  md+=f'### {month} 전체 평가 — 모델별 Macro-F1\n\n'
  rows=[]
  for stage in stages:
   rows.append([stage['id'],*[next((avg(r['macro_f1']['per_seed'],100)for r in summary['rows']if r['stage']==stage['id']and r['month']==month and r['group']=='all'and r['model']==m),'미완료')for m in MODELS]])
  md+=table(['조건',*MODELS],rows)
  md+='### '+month+' 같은 seed의 대응 차이(%p)\n'
  md+=table(['조건','비교',*map(str,SEEDS),'평균±SD','양수반복'],[[r['stage'],r['comparison'],*[f'{v:+.3f}'for v in r['per_seed_pp']],avg(r['per_seed_pp']),f"{r['positive_seeds']}/5"]for r in summary['paired']if r['month']==month])
 md+='\nM2−M1은명시한BN적응정책을포함한사전학습활용비교다. M5−M3이증류의추가효과이고, M2−M5는교사대비학생의성능차이다. 5개차이의부호와크기를함께보며유의성검정없이확정적우위라고말하지않는다.\n\n'
 md+='### 목표와 해석의 한계\n\n'
 for r in summary['paired']:
  if r['month']=='202504'and r['comparison']=='M2−M5':
   md+=f"- {r['stage']}: 교사대비학생F1차이평균 {r['mean_pp']:.3f}%p; 2%p이내반복 {sum(v<=2 for v in r['per_seed_pp'])}/5. 평균기준목표 {'충족'if r['mean_pp']<=2 else '미달'}.\n"
 md+='\n라벨수가늘면공통50epoch에서도update와학습시간이늘어난다. 서비스구성별클래스수·목록·난이도도다르므로점수차이를Google여부하나의인과효과로해석하지않는다. 4·5월은과거에도살펴본시간차평가자료로완전히미사용외부최종검증이아니다.\n\n'
 md+='### CPU 추론 비용\n\n모델마다새프로세스,CPU1스레드·FP32·고정128입력순환·동일warm-up/반복규칙이다. p95평균은모든지연을합친p95가아니다. M0에는16통계추출이포함되며패킷수집대기·파일IO·array변환은제외한다. 입력은20클래스6~7개씩,13클래스9~10개씩총128개로균등에가깝게고정했다. 구성간서로다른입력과시스템부하가있어작은속도차이를모델고유차이로단정하지않는다.\n'
 md+=table(['조건','모델','batch1중앙값평균±SD(ms)','개별p95평균±SD(ms)','128묶음처리량평균±SD(flows/s)','추론파일MiB평균±SD'],[[r['stage'],r['model'],*[avg(r[k]['per_seed'])for k in ['batch1_median_ms','batch1_p95_ms','batch128_flows_s','inference_MiB']]]for r in summary['cpu_rows']])
 for stage in stages:
  sid=stage['id'];md+=f'<details><summary>{sid} 전체·겹침·비겹침·공통미관측</summary>\n\n'
  md+=table(['월','부분집합','모델','N범위','support있는클래스범위','F1평균±SD(%)','정확도평균±SD(%)'],[[r['month'],r['group'],r['model'],f"{min(r['n'])}–{max(r['n'])}",f"{min(r['classes_with_support'])}–{max(r['classes_with_support'])}",avg(r['macro_f1']['per_seed'],100),avg(r['accuracy']['per_seed'],100)]for r in summary['rows']if r['stage']==sid])
  md+='빈부분집합은N/A. 고정클래스수에서support없는클래스처리규칙을유지한다. 희소겹침집단은전체서비스성능추정이아니다.\n\n</details>\n'
  md+=f'<details><summary>{sid} 서비스별F1과교사·학생의주요혼동</summary>\n\n'
  md+=table(['월','서비스','support',*MODELS],[[r['month'],r['service'],r['support'],*[f"{100*r['models'][m]['per_class_f1']:.3f}"for m in MODELS]]for r in summary['class_rows']if r['stage']==sid])
  md+='같은평가플로우에대한5개모델혼동행렬합계이며서로다른플로우5배가아니다. 행=정답,열=예측.\n'
  md+=table(['월','모델','정답→예측','5반복오분류합'],[[r['month'],r['model'],p['true']+'→'+p['predicted'],p['count']]for r in summary['confusions']if r['stage']==sid for p in r['pairs'][:5]])+'\n</details>\n'
 summary['complete']=all(s['fits']==30 and s['evaluations']==60 and s['cpu']==30 for s in summary['stages'])
 summary['new_fits_verified']=sum(s['fits']for s in summary['stages']if s['id']!='mixed_n200')
 summary['new_evaluations_verified']=sum(s['evaluations']for s in summary['stages']if s['id']!='mixed_n200')
 summary['new_cpu_measured']=sum(s['cpu']for s in summary['stages']if s['id']!='mixed_n200')
 out=E/'continuation_recovered';out.mkdir(exist_ok=True)
 (out/'continuation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 (H/'continuation_results.md').write_text(md)
 print(json.dumps({k:summary[k]for k in ['complete','new_fits_verified','new_evaluations_verified','new_cpu_measured']},ensure_ascii=False))
 return summary
if __name__=='__main__':run()
