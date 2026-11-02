"""Render the standalone report from already verified records. Never trains models."""
from pathlib import Path
import json, csv, hashlib, statistics, sys, math, html, os

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E = ROOT/'experiments/2026-10-30_midterm_restart'
P = ROOT/'reports/2026-10-30_midterm_research_record'
A = ROOT/'experiments/2026-10-28_data_audit'
def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
S = read(E/'continuation_recovered/continuation_summary.json')
D = read(E/'prepared/manifest.json')
REG = read(P/'result_registry.json')
DEV = read(ROOT/REG['campaigns'][0]['verification'])
ARCH = read(P/'snapshots/architecture.json')
NAMES = {'mixed_n50':'혼합20 · 50개','mixed_n100':'혼합20 · 100개','mixed_n200':'혼합20 · 200개','mixed_n1000':'혼합20 · 1000개','nongoogle_n200':'비Google13 · 200개','googleonly_n200':'Google계열20 · 200개'}
COHORT = {'google_included20':'혼합20','non_google13':'비Google13','google_only20':'Google계열20'}
ORDER = list(NAMES)
MODELS = ['M0','M1','M2','M3','M4','M5']
LABELS = ['16통계 트리','직접학습 교사','사전학습 교사','직접학습 학생','M1 증류 학생','M2 증류 학생']
COLORS = ['#768393','#4a78ad','#077c82','#9d7cbb','#c8892c','#c3455d']
def f(x, n=3): return 'N/A' if x is None else f'{x:,.{n}f}'
def pct(x): return f(None if x is None else 100*x)
def ms(d, scale=100): return f(d['mean']*scale)+' ± '+f(d['sd']*scale) if d.get('mean') is not None else 'N/A'
def seq(xs, scale=1): return ' / '.join(f(None if x is None else x*scale) for x in xs)
def row(stage, model, month='202504', group='all'):
 return next(r for r in S['rows'] if (r['stage'],r['model'],r['month'],r['group'])==(stage,model,month,group))
def paired(stage,comparison,month='202504'):
 return next(r for r in S['paired'] if (r['stage'],r['comparison'],r['month'])==(stage,comparison,month))
def cost(stage,model):return next(r for r in S['cpu_rows'] if (r['stage'],r['model'])==(stage,model))
def table(head, rows):
 def safe(v):return str(v).replace('|','&#124;').replace('\n',' ')
 return '\n|'+'|'.join(head)+'|\n|'+'|'.join(['---']*len(head))+'|\n'+''.join('|'+'|'.join(safe(x) for x in r)+'|\n' for r in rows)+'\n'
def details(title,body):return '\n<details><summary>'+title+'</summary>\n\n'+body+'\n</details>\n'
def link(p,label=None):
 p=Path(p);rel=p.relative_to(ROOT) if p.is_absolute() else p
 return f'[{label or rel.name}](../../{rel.as_posix()})'
def fig(name,caption):return f'\n<figure><img src="figures/{name}.svg" alt="{html.escape(caption,quote=True)}"><figcaption>{caption}</figcaption></figure>\n'

TR=[]; RUNTIMES={}
for stage in S['stages']:
 base=E/'main_recovered' if stage['id']=='mixed_n200' else E/'continuation_recovered'/stage['id']
 v=read(ROOT/read(base/'training_registry.json')['verification'])
 RUNTIMES[stage['id']]=v.get('runtime')
 for rr in v['records']:
  r=dict(rr);raw=read(ROOT/r['metrics_path']);r['stage']=stage['id']
  r['history_compact']=[{k:val for k,val in h.items() if k!='validation'}|{'validation':{k:val for k,val in h.get('validation',{}).items() if k in ['n','macro_f1','accuracy','gt_cross_entropy']}} for h in raw.get('history',[])]
  r['teacher_prediction_seconds']=raw.get('teacher_prediction_seconds')
  TR.append(r)
assert S['complete'] and len(TR)==180 and len(DEV['records'])==60 and len(S['rows'])==288
assert len({(r['stage'],r['model'],r['seed']) for r in TR})==180

# Standard plotting library is isolated from the experiment environment.
sys.path.insert(0,'/private/tmp/midterm-report-plot')
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/midterm-report-mpl-cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties, fontManager
font_path=Path('/System/Library/Fonts/AppleSDGothicNeo.ttc')
if font_path.exists():
 fontManager.addfont(str(font_path));plt.rcParams['font.family']=FontProperties(fname=str(font_path)).get_name()
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#33445a','text.color':'#24364b','axes.edgecolor':'#cfd8df','grid.color':'#e4e9ee','axes.unicode_minus':False,'svg.fonttype':'path','savefig.facecolor':'white'})
def save(name, fig):
 fig.savefig(HERE/'figures'/f'{name}.svg',bbox_inches='tight');fig.savefig(HERE/'figures'/f'{name}.png',dpi=160,bbox_inches='tight');plt.close(fig)

fig_,ax=plt.subplots(figsize=(10.5,4.1))
y=[row('mixed_n200',m)['macro_f1']['mean']*100 for m in MODELS];err=[row('mixed_n200',m)['macro_f1']['sd']*100 for m in MODELS]
ax.bar(MODELS,y,color=COLORS,width=.58,yerr=err,capsize=4)
for i,v in enumerate(y):ax.text(i,v+err[i]+1.3,f'{v:.2f}',ha='center',weight='bold')
ax.set(ylim=(0,65),ylabel='Macro-F1 (%)',title='대표 조건: 혼합20 · 200개/서비스 · 4월');ax.set_axisbelow(True);ax.grid(axis='y');save('representative',fig_)

fig_,ax=plt.subplots(figsize=(10.5,4.8));budgets=[50,100,200,1000];xx=np.arange(4)
for i,m in enumerate(MODELS):
 a=[row(f'mixed_n{b}',m)['macro_f1'] for b in budgets]
 ax.errorbar(xx,[x['mean']*100 for x in a],yerr=[x['sd']*100 for x in a],marker='o',capsize=3,label=f'{m} {LABELS[i]}',color=COLORS[i],lw=2)
ax.set(xticks=xx,xticklabels=budgets,xlabel='서비스당 fitting 정답 수 (동일 간격의 범주축)',ylabel='4월 Macro-F1 (%)',ylim=(10,70));ax.grid(axis='y');ax.legend(ncol=3,loc='upper center',bbox_to_anchor=(.5,1.2),frameon=False,fontsize=10);save('label_curve',fig_)

fig_,ax=plt.subplots(figsize=(10.5,4.6));xx=np.arange(3);st=['mixed_n200','nongoogle_n200','googleonly_n200']
for i,m in enumerate(MODELS):
 vals=[row(s,m)['macro_f1'] for s in st];ax.bar(xx+(i-2.5)*.12,[v['mean']*100 for v in vals],width=.115,color=COLORS[i],label=m,yerr=[v['sd']*100 for v in vals],capsize=2)
ax.set(xticks=xx,xticklabels=['혼합20','비Google13','Google계열20'],ylabel='4월 Macro-F1 (%)',ylim=(0,95));ax.legend(ncol=6,frameon=False);ax.grid(axis='y');ax.set_axisbelow(True);save('cohorts',fig_)

classes=[r for r in S['class_rows'] if r['stage']=='mixed_n200' and r['month']=='202504']
mat=np.array([[r['models'][m]['per_class_f1']*100 for m in MODELS] for r in classes])
fig_,ax=plt.subplots(figsize=(10.5,8));im=ax.imshow(mat,vmin=0,vmax=100,cmap='YlGnBu',aspect='auto');ax.set(xticks=range(6),xticklabels=MODELS,yticks=range(len(classes)),yticklabels=[r['service'] for r in classes]);ax.tick_params(axis='both',length=0)
for i in range(mat.shape[0]):
 for j in range(6):ax.text(j,i,f'{mat[i,j]:.1f}',ha='center',va='center',color='white' if mat[i,j]>52 else '#26364a',fontsize=9)
fig_.colorbar(im,ax=ax,label='서비스 F1 (%)',shrink=.7);save('class_heatmap',fig_)

fig_,axes=plt.subplots(1,2,figsize=(11,4.2),sharey=True)
for ax,stage in zip(axes,['mixed_n200','mixed_n50']):
 for i,m in enumerate(MODELS[1:],1):
  histories=[r['history_compact'] for r in TR if r['stage']==stage and r['model']==m]
  arr=np.array([[h['validation']['macro_f1']*100 for h in hh] for hh in histories]);assert arr.shape==(5,50)
  av=arr.mean(0);sd=arr.std(0,ddof=1);ax.plot(np.arange(1,51),av,label=m,color=COLORS[i]);ax.fill_between(np.arange(1,51),av-sd,av+sd,color=COLORS[i],alpha=.10)
 ax.set(title=NAMES[stage],xlabel='Epoch',ylim=(0,80));ax.grid(axis='y')
axes[0].set_ylabel('2월 검증 Macro-F1 (%)');axes[1].legend(frameon=False,ncol=3,loc='lower right');save('learning_curves',fig_)

fig_,ax=plt.subplots(figsize=(10.5,4.6))
offsets={'M0':(6,-17),'M1':(6,-17),'M2':(6,7),'M3':(-55,-25),'M4':(12,-5),'M5':(-55,15)}
for i,m in enumerate(MODELS):
 c=cost('mixed_n200',m);r=row('mixed_n200',m);x=c['batch1_median_ms']['mean'];y=r['macro_f1']['mean']*100
 ax.scatter(x,y,s=120,color=COLORS[i],edgecolor='white',zorder=3);ax.annotate(m,(x,y),xytext=offsets[m],textcoords='offset points',weight='bold',color=COLORS[i]);ax.errorbar(x,y,yerr=r['macro_f1']['sd']*100,color=COLORS[i],capsize=3,alpha=.6)
ax.set(xscale='log',xlim=(.025,.7),ylim=(25,60),xlabel='CPU batch1 median 지연 (ms, 로그축) — 왼쪽이 빠름',ylabel='4월 Macro-F1 (%) — 위쪽이 높음')
from matplotlib.ticker import FixedLocator, FixedFormatter, NullLocator
ticks=[.03,.04,.06,.1,.2,.3,.4,.6]
ax.xaxis.set_major_locator(FixedLocator(ticks));ax.xaxis.set_major_formatter(FixedFormatter([str(x) for x in ticks]));ax.xaxis.set_minor_locator(NullLocator())
ax.grid();save('cost_accuracy',fig_)

AUDIT=list(csv.DictReader((A/'clipped_summary.csv').open()))
coll=[r for r in AUDIT if r['cohort']=='google_included20' and r['period']=='202501' and r['policy']=='padded'];coll.sort(key=lambda x:int(x['packets']))
assert len(coll)==30
fig_,ax=plt.subplots(figsize=(10.5,4.1));ax.plot([int(r['packets']) for r in coll],[float(r['conflicting_rate'])*100 for r in coll],color='#077c82',marker='o',ms=4);ax.set(xlabel='첫 k개 패킷',ylabel='충돌 기록 비율 (%)',xticks=[1,5,10,15,20,25,30],ylim=(0,105));ax.grid();save('collision',fig_)

blocks={}
blocks['MAIN_HERO']=fig('representative','그림 1. 동일한 혼합20·200개 조건의 4월 All 평가. 막대는5개 seed 평균, 오차막대는표본 SD. M0–M5의 역할은7장에 설명한다.')
blocks['COHORTS']=table(['구성','분류 클래스','학습 예산/서비스','목적'],[['혼합20','Google 계열과 비Google 서비스가 함께 있는20개','50·100·200·1000','대표 비교·라벨 곡선'],['비Google13','Google을 제외한13개','200','다른 서비스 구성에서 비교'],['Google계열20','YouTube·Firebase 등을 포함한Google계열20개','200','같은 사업자 내부 구분']])
blocks['DATA_COUNTS']=table(['구성','1월 정제 후 후보','2월 검증','4월 평가','5월 평가'],[[COHORT[c],f(d['january_curation']['retained_unique_inputs'],0),sum(d['validation_support']),f(d['evaluation_202504']['rows'],0),f(d['evaluation_202505']['rows'],0)] for c,d in D['cohorts'].items()])
blocks['CLEANUP']=table(['구성','1월 입력','충돌 그룹','충돌 기록 제외','동일라벨 중복 초과분','남은 고유 입력'],[[COHORT[c]]+[f(d['january_curation'][k],0) for k in ['input_rows','conflicting_groups','conflicting_rows','same_label_duplicate_excess','retained_unique_inputs']] for c,d in D['cohorts'].items()])
blocks['COLLISION_FIGURE']=fig('collision','그림 2. 혼합20·1월567,806개에서 입력 길이만 늘려 비교한 충돌률. 짧은 플로우를 패딩해 분모를 고정했다. 학습 모델의 오분류율 그래프가 아니다.')
blocks['COLLISION_TABLE']=table(['첫 k패킷','충돌 그룹','충돌 기록','충돌 기록 비율','경험적 최소 오류 비율'],[[r['packets'],f(int(r['conflicting_patterns']),0),f(int(r['conflicting_rows']),0),pct(float(r['conflicting_rate']))+'%',pct(float(r['empirical_minimum_error_rate']))+'%'] for r in coll if int(r['packets']) in [1,2,5,10,20,30]])
blocks['MATRIX']=table(['구성','50개','100개','200개','1000개','학습 합계'],[['혼합20','30fit','30fit','30fit','30fit','120fit'],['비Google13','미실행','미실행','30fit','미실행','30fit'],['Google계열20','미실행','미실행','30fit','미실행','30fit'],['합계','30','30','90','30','180fit']])
blocks['MODEL_MAP']=table(['모델','구조/시작점','학습 신호','비교 역할'],[['M0','16통계 → LightGBM','정답','전통적 기준선'],['M1','큰 CNN, 공개 학습 가중치 미사용','정답 CE','목표 데이터 직접학습 교사'],['M2','M1과 같은 구조, 공개 사전학습 가중치','정답 CE, 전체 미세조정','사전학습 활용 교사'],['M3','작은3층CNN','정답 CE','KD 없는 학생 기준선'],['M4','M3와 동일한 작은CNN','정답 CE + M1 확률 KL','직접학습 교사에서 증류'],['M5','M3와 동일한 작은CNN','정답 CE + M2 확률 KL','사전학습 교사에서 증류']])
blocks['DEV_SELECTION']=details('개발 후보 평균 점수 보기 — 모두2월 검증, 본평가 아님',table(['모델','후보','검증 Macro-F1 (%)','정답 CE'],[[m,r['candidate'],pct(r['mean_macro_f1']),f(r['mean_gt_ce'])] for m,rs in DEV['selection']['lr_comparisons'].items() for r in rs])+table(['α','T','학생4개 평균 검증F1 (%)','평균 정답 CE'],[[r['alpha'],r['temperature'],pct(r['mean_macro_f1']),f(r['mean_gt_ce'])] for r in DEV['selection']['kd_grid']]))
blocks['REPRESENTATIVE']=table(['모델','4월 F1 (%)','4월 Accuracy (%)','5월 F1 (%)','5월 Accuracy (%)'],[[m,ms(row('mixed_n200',m)['macro_f1']),ms(row('mixed_n200',m)['accuracy']),ms(row('mixed_n200',m,'202505')['macro_f1']),ms(row('mixed_n200',m,'202505')['accuracy'])] for m in MODELS])
blocks['LABEL_FIGURE']=fig('label_curve','그림 3. 혼합20의4월 All 평가. 동일 검증·평가 자료에서 학습 예산을 바꿨다. 점과오차막대는평균±SD. 가로축 간격은50/100/200/1000의 범주이며 선형 수치 간격이 아니다.')
blocks['LABEL_TABLE']=table(['서비스당 정답']+MODELS,[[b]+[ms(row(f'mixed_n{b}',m)['macro_f1']) for m in MODELS] for b in [50,100,200,1000]])
comparisons=['M2−M1','M5−M3','M5−M4','M2−M5']
blocks['PAIRED_TABLE']=table(['4월 조건']+[x+' (%p)' for x in comparisons],[[NAMES[s]]+[f"{paired(s,c)['mean_pp']:+.3f} ± {paired(s,c)['sd_pp']:.3f} ({paired(s,c)['positive_seeds']}/5)" for c in comparisons] for s in ORDER])+'\n괄호는 차이가 양수인 seed 수다. 양수 반복 수는 유의성 검정 결과가 아니다.\n'
blocks['COHORT_FIGURE']=fig('cohorts','그림 4. 예산200개에서 서비스 구성을 바꾼 비교. 평균±SD. 클래스 수와 구성이 다른 문제이므로 Google 여부의 단일 요인 효과로 읽지 않는다.')
blocks['COHORT_RESULTS']=table(['4월 구성']+MODELS,[[NAMES[s]]+[ms(row(s,m)['macro_f1']) for m in MODELS] for s in st])
blocks['CLASS_FIGURE']=fig('class_heatmap','그림 5. 대표 혼합20·200개·4월의 서비스별F1. 각 칸은5개 seed 평균(%). 클래스별 support는 다음 표와 부록 C에 제공한다.')
blocks['CLASS_HIGHLIGHTS']=table(['서비스','support','M2 F1 (%)','M5 F1 (%)','M2 정밀도 (%)','M2 재현율 (%)'],[[r['service'],f(r['support'],0),pct(r['models']['M2']['per_class_f1']),pct(r['models']['M5']['per_class_f1']),pct(r['models']['M2']['per_class_precision']),pct(r['models']['M2']['per_class_recall'])] for r in classes if r['service'] in ['instagram','snapchat','youtube','google-www','google-drive','google-translate','google-imasdk']])
blocks['CONFUSION_HIGHLIGHTS']=table(['4월 구성·모델','실제 → 예측','5개 seed 합산 건수'],[[NAMES[r['stage']]+' · '+r['model'],p['true']+' → '+p['predicted'],f(p['count'],0)] for r in S['confusions'] if (r['stage'],r['model'],r['month']) in [('mixed_n200','M2','202504'),('googleonly_n200','M5','202504'),('nongoogle_n200','M5','202504')] for p in r['pairs'][:2]])
blocks['OVERLAP']=table(['4월 조건','실제 학습 겹침 N (seed201→205)','M5 All F1 (%)','M5 비겹침 F1 (%)','M5 공통미노출 F1 (%)'],[[NAMES[s],'/'.join(map(str,row(s,'M5',group='train_overlap')['n'])),ms(row(s,'M5')['macro_f1']),ms(row(s,'M5',group='train_nonoverlap')['macro_f1']),ms(row(s,'M5',group='common_unseen')['macro_f1'])] for s in ORDER])
blocks['LEARNING_FIGURE']=fig('learning_curves','그림 6. 본실험의2월 검증곡선. 실선은5개 seed 평균, 음영은±표본 SD. 모든checkpoint는각 seed의검증 best로선택하므로 평균곡선 최고점과 선택epoch가 같을 필요는 없다.')
blocks['CURVE_TABLE']=table(['조건','M2 선택epoch (201→205)','M2 검증 best F1 (%)','M5 검증 best F1 (%)'],[[NAMES[s],'/'.join(str(r['selected_step']) for r in sorted(TR,key=lambda x:x['seed']) if r['stage']==s and r['model']=='M2'),pct(statistics.mean(r['validation']['macro_f1'] for r in TR if r['stage']==s and r['model']=='M2')),pct(statistics.mean(r['validation']['macro_f1'] for r in TR if r['stage']==s and r['model']=='M5'))] for s in ORDER])
blocks['MONTH_CHANGE']=table(['조건','M2 4월→5월 (%)','M5 4월→5월 (%)','M2 변화 (%p)','M5 변화 (%p)'],[[NAMES[s]]+[pct(row(s,m)['macro_f1']['mean'])+' → '+pct(row(s,m,'202505')['macro_f1']['mean']) for m in ['M2','M5']]+[f((row(s,m,'202505')['macro_f1']['mean']-row(s,m)['macro_f1']['mean'])*100) for m in ['M2','M5']] for s in ORDER])
blocks['COST_FIGURE']=fig('cost_accuracy','그림 7. 대표 조건의 성능과CPU 지연. 위로갈수록성능이높고 왼쪽일수록빠르다. 세학생의시간은가까워서 라벨을분리해표시했다. 세로오차막대는F1의SD다.')
blocks['CPU_TABLE']=table(['모델','파라미터','batch1 median (ms)','batch1 p95 (ms)','batch128 (flows/s)','추론파일 MiB','warm RSS MiB'],[[m,f(cost('mixed_n200',m)['parameters'],0)]+[f(cost('mixed_n200',m)[k]['mean'],3 if k in ['batch1_median_ms','batch1_p95_ms','inference_MiB'] else 1) for k in ['batch1_median_ms','batch1_p95_ms','batch128_flows_s','inference_MiB','warm_RSS_MiB']] for m in MODELS])

# Detailed appendices are generated, not transcribed from the rounded prose.
app=['## 부록 A. 결정표와 개발 60회 전체 기록\n\n읽기 흐름을 위해 접어 두었지만 모든 후보와 반복을 포함했다. 본문 표는 아래의 원본 수치에서 반올림한다. 원본 파일 링크는 프로젝트 폴더 구조가 함께 있을 때 열린다. 그래프와 아래 표는 HTML 자체에 포함된다.']
decision_rows=[
 ['첫30 PPI','제한된 관측 정보·공개 교사 호환·같은정보 비교','전체 FLOWSTATS·payload·도메인 미사용'],
 ['짧은플로우 포함','길이로 쉬운자료만남기는 편향방지','패딩·DIR마스크, 길이별support보존'],
 ['1월 충돌격리·동일라벨대표1개','같은관측값 반복·상충학습 신호 관리','평가의반복과충돌은유지'],
 ['서비스 자격≥1000','최대 fitting예산에서 복제없이비교','1월 정제기준, 후속월조건아님'],
 ['1월/2월/4월/5월','학습·설정선택·시간차평가 구분','4·5월 완전미사용 외부자료아님'],
 ['균등·중첩예산','동일표본에서 예산효과 비교','50⊂100⊂200⊂1000'],
 ['pooled448 교사','실제전이경로를 명시','공개256embedding 끝단과다름'],
 ['M2 전체 미세조정·BN통계유지','선언한저라벨적응정책','최적정책을입증한것은아님'],
 ['단순3층학생','작고명확한경량기준선','최적학생 구조 탐색없음'],
 ['M3/M4/M5 초기값·순열대응','학습 신호차이에초점','교사별독립구조튜닝없음'],
 ['공통α·T','교사별KD선택차이축소','9조합×2교사×2개 seed'],
 ['개발2개 seed·본실험5개 seed','선택과반복평가 분리','seed는표본·초기값·순서를함께변경'],
 ['50 epoch·best 선택','공통 일정과2월선택 규칙','수렴·동일계산량보장은아님'],
 ['M0 CPU1 / 신경망CUDA','트리 기준선과GPU신경망학습','CPU추론측정은본학습과구분'],
 ['All + 겹침분해','자연빈도와입력재등장 함께확인','적은overlap표본 일반화금지'],
 ['5개 seed 평균·SD·짝차이','평균과반복 변동동시에표시','유의성 검정·CI미계산'],
 ['성과와미측정분리','실험완료와목표 달성구분','실시간 캡처·새망·선택확장은별도']]
app.append(details('선택한 규칙과 이유',table(['결정','목적','해석 조건'],decision_rows)))
app.append(details('개발 60회 — 각 후보의2월 검증 best와 원본',table(['모델','seed','LR / leaves','α / T','best step','완료step','검증F1 (%)','Accuracy (%)','GT CE','원본'],[[r['model'],r['seed'],r['lr'] if r['lr'] is not None else 'leaves='+str(r['num_leaves']),str(r['alpha'])+' / '+str(r['temperature']),r['selected_step'],r['completed_steps'],pct(r['validation']['macro_f1']),pct(r['validation']['accuracy']),f(r['validation']['gt_cross_entropy']),link(r['source_metrics'],'metrics')] for r in DEV['records']])))

app.append('## 부록 B. 서비스·표본 수와 데이터 진단\n\n클래스별 행의 순서는 실제 출력 인덱스 순서다. 1월 입력은 정제 전, 1월 고유 후보는 정제 후다. 2월 전체와 실제 검증 표본을 구분한다.')
for c,d in D['cohorts'].items():
 rows=[[i,n,d['codes'][i],d['month_support']['202501'][i],d['january_curation']['retained_per_class'][n],d['month_support']['202502'][i],d['validation_support'][i],d['month_support']['202504'][i],d['month_support']['202505'][i]] for i,n in enumerate(d['classes'])]
 app.append(details(COHORT[c]+' — 전체 서비스 목록·월별support',table(['index','서비스','APP코드','1월입력','1월고유후보','2월전체','검증사용','4월','5월'],rows)))
app.append(details('2월 검증과 준비된 학습목록의 입력 겹침', '아래는 검증 기록 중 해당 준비 목록에 포함된 PPI와 같은 입력의 수다. main행은 최대 1000개/서비스 목록 기준이므로 실제 200개 학습과의 겹침 수로 그대로 읽으면 안 된다. 원본 ID 겹침과는 다르며, 이 표가0이 아닌데 검증 입력이 완전히 독립이라고 표현하지 않는다.\n'+table(['구성','준비목록','목록기록수','최대개수/서비스','같은PPI 검증기록'],[[COHORT[c],k,v['rows'],v['per_class'],v['validation_overlap_rows']] for c,d in D['cohorts'].items() for k,v in d['runs'].items()])))
app.append(details('길이가30 미만인 평가기록과 공통미노출 support', 'short는 기록된 유효 패킷 수<30이다. short/long별 성능은 아직 집계하지 않았다.\n'+table(['구성','월','All','short','long','Common-unseen','검증PPI와겹침'],[[COHORT[c],mo,d['evaluation_'+mo]['rows'],d['evaluation_'+mo]['groups']['short_flow'],d['evaluation_'+mo]['rows']-d['evaluation_'+mo]['groups']['short_flow'],d['evaluation_'+mo]['groups']['common_unseen'],d['evaluation_'+mo]['groups']['validation_overlap']] for c,d in D['cohorts'].items() for mo in ['202504','202505']])))
app.append(details('첫1–30패킷 충돌 — 혼합20의12개월 및 월통합 진단', '정규화 PPI·padded 정책만 제시한다. 월 통합 ALL은 월 내 충돌을 더한 값이 아니라 여러 달을 함께 그룹화한 결과다. 이 진단의 후속 월 라벨을 1월 학습 정제에 교차 사용하지 않았다.\n'+table(['기간','k','기록수','고유패턴','충돌그룹','충돌기록','충돌률 (%)','경험적 최소 오류수'],[[r['period'],r['packets'],r['rows'],r['unique_patterns'],r['conflicting_patterns'],r['conflicting_rows'],pct(float(r['conflicting_rate'])),r['empirical_minimum_errors']] for r in AUDIT if r['cohort']=='google_included20' and r['policy']=='padded'])))
app.append(details('다른 후보 구성·원본 PPI·통계 결합 진단 자료', '서비스 자격을 확정하기 전의 비Google20·Google계열24와 최종 비Google13·Google계열20은 클래스 구성이 다르다. 아래 진단 자료는 후보 구성, raw/clipped 표현, padded/최소길이 정책, 월별 분석을 모두 보존한다. 진단 결과를 최종 본실험 점수와 섞지 않는다. 통계 결합의 충돌 검사는 입력 모호성 진단이며, FLOWSTATS 모델을 학습해 성능을 비교했다는 뜻은 아니다.\n\n'+' · '.join(link(A/f,label) for f,label in [('raw_summary.csv','원본 PPI의1–30패킷 진단'),('clipped_summary.csv','정규화 PPI의1–30패킷 진단'),('clipped_by_service.csv','서비스별 진단'),('packet_length_by_month_service.csv','월·서비스별 패킷 길이'),('flowstats_collision_check.json','통계 결합 진단의 정의·검사 결과')])) )
quality=list(csv.DictReader((A/'quality_by_day_service.csv').open()))
qkeys=[k for k in quality[0] if k not in ['month','day','code','service','rows']]
app.append(details('원본 자료 품질진단 범위와 검사항목', '로컬 원본10,000,000기록의 ID는 모두 고유했다. 아래는 품질 진단 CSV의 일자×서비스 행에서 각 항목을 합산한 값이다. 항목이 서로 배타적이지 않으므로 합을 제외 기록 수로 해석하지 않는다. `port_not_443`·`empty_sni` 등은 진단 항목이며 자동 제거 기준은 아니다.\n'+table(['진단 항목','기록수 합'],[[k,sum(int(r[k]) for r in quality)] for k in qkeys])+link(A/'quality_by_day_service.csv','일자·서비스별 품질원본')+' · '+link(A/'analyze.py','진단·유효성 처리 코드')+'\n\n원본 HDF5 크기: 3,544,625,537 bytes. 원본 자료의 날짜 누락: 2024-10-31, 2024-12-11~14. 본실험의 월별 개수는 이 보고서의 고정 manifest를 따른다. 원본10,000,000개 중 진단 대상 서비스 합집합 캐시는6,456,131개이며 이를 실제 학습 표본 수로 세지 않는다.'))

app.append('## 부록 C. 본실험 180회·360월평가·180CPU측정 전체 결과\n\n세 자리 반올림 표와 더 정밀한 기계 판독 값을 함께 제공한다. <button class="inline-button" id="export-data">이 보고서의 수치·학습곡선 JSON 저장</button> 새 모델을 학습하거나 다시 측정한 것이 아니라 검증된 결과의 보고용 복사본이다.')
for stage in ORDER:
 rr=sorted([r for r in TR if r['stage']==stage],key=lambda r:(r['model'],r['seed']))
 app.append(details(NAMES[stage]+' — 30개 학습 및60개 월평가',table(['모델','seed','best/완료 step','2월F1 (%)','4월F1 (%)','4월Acc (%)','4월CE','5월F1 (%)','5월Acc (%)','5월CE','fit초','원본'],[[r['model'],r['seed'],str(r['selected_step'])+'/'+str(r['completed_steps']),pct(r['validation']['macro_f1'])]+[pct(row(stage,r['model'],mo)[key]['per_seed'][r['seed']-201]) if key!='gt_cross_entropy' else f(row(stage,r['model'],mo)[key]['per_seed'][r['seed']-201]) for mo in ['202504','202505'] for key in ['macro_f1','accuracy','gt_cross_entropy']]+[f(r['resources']['full_fit_seconds'],2),link(r['metrics_path'],'metrics')] for r in rr])+'\nfit초는 초기화·교사 예측·학습/검증·checkpoint I/O를 포함하고 archive 생성을 제외한 실행기 기록이다. M4/M5행에 이미 완료된 교사의 fit시간이 자동으로 더해지는 것은 아니다. M0 step은 round, 신경망 step은 epoch다.'))
for stage in ORDER:
 rows=[r for r in S['rows'] if r['stage']==stage]
 app.append(details(NAMES[stage]+' — All·겹침·비겹침·공통미노출 전체 집계',table(['월','집합','모델','N (201→205)','정답등장클래스 수','F1 평균±SD (%)','Acc 평균±SD (%)','GT CE 평균±SD'],[[r['month'],r['group'],r['model'],'/'.join(map(str,r['n'])),'/'.join(map(str,r['classes_with_support'])),ms(r['macro_f1']),ms(r['accuracy']),ms(r['gt_cross_entropy'],1)] for r in rows])))
app.append(details('짝지은 모델 차이60개 — 5개 seed를 모두 표시',table(['조건','월','차이','201','202','203','204','205','평균±SD (%p)','양수반복'],[[NAMES[r['stage']],r['month'],r['comparison']]+[f(x) for x in r['per_seed_pp']]+[f(r['mean_pp'])+' ± '+f(r['sd_pp']),str(r['positive_seeds'])+'/5'] for r in S['paired']])))
for stage in ORDER:
 cr=[r for r in S['class_rows'] if r['stage']==stage]
 app.append(details(NAMES[stage]+' — 모든 서비스 Precision·Recall·F1', '각 P/R/F는5개 seed 평균(%). support는 평가 기록 수이며5배 하지 않는다.\n'+table(['월','서비스','support']+[m+' P / R / F' for m in MODELS],[[r['month'],r['service'],r['support']]+[' / '.join(pct(r['models'][m][k]) for k in ['per_class_precision','per_class_recall','per_class_f1']) for m in MODELS] for r in cr])))
app.append(details('M2·M5 주요 혼동 쌍 — 조건·월별 상위10개', '건수는 동일 평가 플로우의5개 seed 예측을 합한 값이다. 전체 행렬과 seed별 상세는 월별 원본 평가 지표에 보존되어 있다.\n'+table(['조건','월','모델','실제','예측','합산건수'],[[NAMES[r['stage']],r['month'],r['model'],p['true'],p['predicted'],p['count']] for r in S['confusions'] for p in r['pairs']])))
app.append(details('CPU180개 측정 — seed별 비용',table(['조건','모델','seed','batch1 median ms','batch1 p95 ms','batch128 flows/s','파일 MiB','warm RSS MiB'],[[NAMES[r['stage']],r['model'],201+i]+[f(r[k]['per_seed'][i],4 if 'ms' in k else 2) for k in ['batch1_median_ms','batch1_p95_ms','batch128_flows_s','inference_MiB','warm_RSS_MiB']] for r in S['cpu_rows'] for i in range(5)])))
app.append(details('학습 자원·교사 연결·초기 상태·checkpoint 식별',table(['조건','모델','seed','fit초','교사예측초','CUDA peak allocated MiB','초기state SHA(앞12)','교사 SHA(앞12)','best SHA(앞12)','checkpoint'],[[NAMES[r['stage']],r['model'],r['seed'],f(r['resources']['full_fit_seconds'],2),f(r['teacher_prediction_seconds'],3),f(r['resources'].get('cuda_peak_allocated_bytes',0)/2**20,2),(r.get('initial_state_sha256') or 'N/A')[:12],(r.get('teacher_checkpoint_sha256') or 'N/A')[:12],r['checkpoint_sha256'][:12],link(r['checkpoint'],'원본')] for r in TR])+'\n표에는 해시 앞12글자를 표시했으며 전체 해시는 JSON과 원본 registry에 있다. CUDA allocation은 GPU 전체 메모리·전력·청구 비용과 다르다.'))

app.append('## 부록 D. 구조·재현 환경·근거 파일\n\n수치가 필요할 때 원본을 찾을 수 있도록 입력→학습→평가→보고서를 연결한다. 이 보고서는 기존 연구 원장과 원본 파일을 변경하지 않고 별도로 생성했다.')
for m in ['M1','M3']:
 a=ARCH['models'][m]
 app.append(details(m+' 실제 모듈과 직접 소유 파라미터',table(['모듈','종류','직접파라미터','정의'],[[r['name'],r['type'],r['parameters_direct'],r['description']] for r in a['modules']])+'\n전체 파라미터 공식: 교사686,613+449C, 학생18,880+65C. M2는 M1 구조, M4/M5는 M3 구조다. 모듈별 직접 소유 수와 재귀 합계를 중복해서 더하지 않는다.'))
app.append(details('환경과 실행 설정',table(['항목','A100 신경망 학습','로컬 CPU 추론'],[['장치','NVIDIA A100-SXM4-40GB','Apple M5, macOS27.0.1 arm64'],['Python','3.13.16','3.12.14'],['PyTorch','2.11.0+cu130','2.14.0'],['NumPy','2.1.3','2.5.3'],['cesnet-models','0.4.1','0.4.1'],['LightGBM','4.6.0','4.6.0'],['정밀도','FP32, TF32 off','FP32'],['스레드','트리CPU1','CPU1'],['설정권위','main_frozen / continuation_frozen','CPU benchmark metadata']])+ '\n원본 config의 준비 단계 `epochs_frozen=false` 등은 해시 보존을 위해 남아 있다. 실제 본실험에서는 별도 동결 설정을 검증한 뒤 실행했다. 원본 config의 주석 한 줄만으로 최종 실행 상태를 판단하지 않는다.'))
evidence=[E/'prepared/manifest.json',E/'config.json',E/'main_frozen.json',E/'continuation_frozen.json',E/'models.py',E/'training.py',E/'data.py',P/'snapshots/architecture.json',E/'continuation_recovered/continuation_summary.json',E/'continuation_recovered/completion.json',E/'continuation_recovered/runtime_release.json',E/'cpu_demo_verification.json',E/'demo_evidence/browser_check.json',E/'continuation_recovered/final_closeout.json']
app.append(details('주요 근거 경로·SHA256',table(['자료','SHA256'],[[link(p),sha(p)] for p in evidence])))
app.append(details('원본 등록부 — 단계별 학습·평가·CPU',table(['등록부','SHA256'],[[link(r['path']),r['sha256']] for r in S['source_registries']])+ '\n개발원본: '+link(ROOT/REG['campaigns'][0]['verification'],'개발 60회 검증결과')+'\n\n원본HDF5 SHA256: `'+D['source_sha256']+'`\n\n공개가중치 SHA256: `dc4b3333388239ac25b8c028c922965e2333cc151dd5fad951950099e86fabc4`'))
app.append(details('검증한 것·미측정 항목·실행 사건', '''평가 예측은 원본 ID·정답·예측 라벨·정답 log확률·최대확률로 보존했다. 전체 클래스 확률벡터는 월별 원본에 모두 보존하지 않았지만, checkpoint와 고정 입력에서 재계산할 수 있다. 학습과 CPU 환경이 달라 모든 플랫폼의 bitwise 동일 출력까지 보장하지 않는다.

검증은 전체 SHA256·ZIP CRC·안전 경로·내부 해시, 실행 수·checkpoint·입력 ID/값/라벨 대응, 학생 초기값·교사 연결, 신경망50 epoch, 보존 예측에서 재계산한 지표를 포함한다. 원본 HDF5와 캐시는4개월48기록을 spot-check했고, overlap은 월·구성별256기록을 다른 byte-set 계산으로 대조했다. 이는 같은 작성자의 다른 계산 방식이며 독립 연구자의 전수 검증은 아니다.

실행 중 세션 소실로 PID2161의30fit을 회수하지 못했다. 이 결과는 성과에서 제외했고, 고정된 동일 설계로 회수한 실행만 집계했다. 작은 연결 점검과3개2 epoch 속도 측정도 개발60/본실험180의 성능 집계에 넣지 않았다. 실행 실패나 호환성 조정은 원장에 보존했다.

후속150fit의 학습·원격 평가 실행은 약76.21분이었다. 전송·회수·유휴 시간과 같지 않고, 실제 과금 명세나 최종 컴퓨팅 유닛 소비를 확인한 값도 아니다. 후속 회수 원본11ZIP은1,867,641,943bytes이며 무결성 확인 뒤2026-10-31 03:07:35 KST에 A100 해제를 기록했다. 추가 GPU 학습은 수행하지 않았다.

미측정 항목도 구분한다. 학습 batch별 전체 시간, 개별 CPU 측정의 정확한 벽시계 시작/종료 전부, 전체 호스트 부하·온도 통제, 전력·실제 청구 금액, 새로운 망·단말별 독립성, 실시간 수집, short/long별 분류 성능, 통계적 유의성 검정은 이번에 완료한 항목이 아니다.
'''))

app.append('## 부록 E. 발표 질의응답\n\n관찰과 가설, 구현 완료와 목표 달성을 구분해서 답한다.')
qa=read(HERE/'qa.json')
for q,a in qa:app.append(details(q,a))

app.append('## 부록 F. 연구 기반과 출처\n\n원 논문·공식 자료에서 가져온 기반과 이번 연구에서 정의한 부분을 구분한다. 문헌의 점수를 우리 데이터의 성능으로 옮겨 적지 않는다.\n'+table(['출처','사용한 기반','이번 연구의 적용·차이'],[
 ['[CESNET-QUICEXT-25 공식 데이터셋](https://zenodo.org/records/17249078)','공개QUIC플로우와패킷정보','로컬XS파일의고정서비스·월·정제를사용'],
 ['[Waiting for QUIC (2025)](https://doi.org/10.1145/3768988)','데이터셋페이지가안내하는인용문헌','이번분류모델설계의성능근거와는구분'],
 ['[Universal Embedding Function…](https://arxiv.org/abs/2502.12930)','QUIC도메인사전학습표현의전이','공개30pktTCNET가중치→pooled448→목표CE미세조정'],
 ['[CESNET Models](https://github.com/CESNET/cesnet-models) · [tc-transfer](https://github.com/CESNET/tc-transfer)','구조·공개가중치·전이구현','실행버전0.4.1,학생과실험조건은본보고서명시'],
 ['[Distilling the Knowledge in a Neural Network (2015)](https://arxiv.org/abs/1503.02531)','교사확률분포를학생 학습에이용','단일대응교사·정답 CE+KL·공통α/T·동일fitting입력'],
 ['[LightGBM (2017)](https://papers.nips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html)','효율적인GBDT학습방법','첫30PPI에서정의한16통계의M0기준선'],
 ['우리 실험의검증된원본','데이터manifest·metrics·checkpoint·예측·CPU측정','표·그래프의직접 수치 근거, 부록 D의경로참조']]))
blocks['APPENDICES']='\n'.join(app)
content=(HERE/'content.md').read_text()
for key,val in blocks.items():
 marker='<!-- '+key+' -->';assert marker in content,key;content=content.replace(marker,val)
assert '<!-- ' not in content
(HERE/'report.md').write_text(content)

compact_dev=[{k:v for k,v in r.items() if k not in ['history','validation','per_class_precision','per_class_recall']}|{'validation':r['validation'],'history_compact':[{k:v for k,v in h.items() if k!='validation'}|{'validation':{k:v for k,v in h.get('validation',{}).items() if k in ['n','macro_f1','accuracy','gt_cross_entropy']}} for h in r['history']]} for r in DEV['records']]
data={'scope':'Verified frozen study only; generated reporting copy, no training','summary':S,'data_manifest':D,'development_selection':DEV['selection'],'development_runs':compact_dev,'main_training':TR,'runtime':RUNTIMES,'architecture':ARCH,'evidence':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in evidence]}
(HERE/'report_data.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False))
print(json.dumps({'chapters':11,'appendices':6,'development_fits':len(compact_dev),'main_fits':len(TR),'monthly_evaluations':len(TR)*2,'cpu_models':len(S['cpu_rows'])*5,'figures':7,'markdown_chars':len(content),'data_bytes':(HERE/'report_data.json').stat().st_size},ensure_ascii=False))
