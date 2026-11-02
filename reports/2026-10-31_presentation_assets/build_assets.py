"""Publication-style presentation assets from saved, verified results. No fitting."""
from pathlib import Path
import os, sys, json, csv, hashlib, html, zipfile, textwrap
sys.path.insert(0, '/private/tmp/midterm-report-plot')
os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/midterm-report-mpl-cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.font_manager import fontManager, FontProperties
from matplotlib.ticker import FixedLocator, FixedFormatter, NullLocator
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPORT = ROOT/'reports/2026-10-31_midterm_report'
SOURCE = REPORT/'report_data.json'
D = json.loads(SOURCE.read_text()); S=D['summary']; MAN=D['data_manifest']
E=ROOT/'experiments/2026-10-30_midterm_restart'
for folder in ['png','svg','svg_text','data','review']:(HERE/folder).mkdir(parents=True,exist_ok=True)
font_path='/System/Library/Fonts/AppleSDGothicNeo.ttc'
fontManager.addfont(font_path)
FONT=FontProperties(fname=font_path).get_name()
plt.rcParams.update({'font.family':[FONT,'DejaVu Sans'],'font.size':14,'axes.unicode_minus':False,
    'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#B8C8CF',
    'axes.labelcolor':'#29404B','text.color':'#193744','xtick.color':'#47606B',
    'ytick.color':'#47606B','grid.color':'#E4EBEF','svg.fonttype':'path',
    'savefig.facecolor':'white','figure.facecolor':'white'})
INK='#193744';MUTED='#5B707A';TEAL='#077C82';BLUE='#4A78AD';PINK='#C3455D'
LIGHT='#F1F6F8';LINE='#D7E3E8';GOLD='#C8892C';PURPLE='#9D7CBB'
MODELS=['M0','M1','M2','M3','M4','M5']
COLORS=dict(zip(MODELS,['#768393',BLUE,TEAL,PURPLE,GOLD,PINK]))
LABELS=dict(zip(MODELS,['PPI 통계 트리','직접학습 교사','사전학습 교사','직접학습 학생','M1 증류 학생','M2 증류 학생']))
STAGES=['mixed_n50','mixed_n100','mixed_n200','mixed_n1000','nongoogle_n200','googleonly_n200']
STAGELABEL=['혼합20 · 50','혼합20 · 100','혼합20 · 200','혼합20 · 1,000','비Google13 · 200','Google 계열20 · 200']
COHORTS={'mixed_n200':'혼합20','nongoogle_n200':'비Google13','googleonly_n200':'Google 계열20'}
ASSETS=[];CHECKS=[];SOURCES={str(SOURCE.relative_to(ROOT)):hashlib.sha256(SOURCE.read_bytes()).hexdigest()}

def source(p):
    p=Path(p);SOURCES[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    return json.loads(p.read_text())
def row(stage,model,month='202504',group='all'):
    return next(r for r in S['rows'] if (r['stage'],r['model'],r['month'],r['group'])==(stage,model,month,group))
def cost(stage,model):return next(r for r in S['cpu_rows'] if r['stage']==stage and r['model']==model)
def pair(stage,comp,month='202504'):
    return next(r for r in S['paired'] if (r['stage'],r['comparison'],r['month'])==(stage,comp,month))
def tx(ax,x,y,s,size=16,weight='normal',color=INK,ha='left',va='center',**kw):
    return ax.text(x,y,s,fontsize=size,fontweight=weight,color=color,ha=ha,va=va,linespacing=1.45,**kw)
def base(code,title,subtitle,footer=''):
    fig=plt.figure(figsize=(16,9));ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,16),ylim=(0,9));ax.axis('off')
    ax.add_patch(Rectangle((.48,8.57),.07,.20,facecolor=TEAL,edgecolor='none'))
    tx(ax,.70,8.67,code+'  /  CAPSTONE · QUIC TRAFFIC CLASSIFICATION',10.5,color=MUTED)
    tx(ax,.65,8.08,title,26,'bold')
    tx(ax,.67,7.55,subtitle,13,color=MUTED)
    ax.plot([.65,15.35],[.72,.72],color=LINE,lw=1)
    tx(ax,.68,.39,footer,10.5,color=MUTED)
    tx(ax,15.3,.39,code,10.5,color=MUTED,ha='right')
    return fig,ax
def box(ax,x,y,w,h,title,body='',color=TEAL,fs=16,bodyfs=14,fill=LIGHT):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.02,rounding_size=0.12',facecolor=fill,edgecolor=LINE,lw=1.1))
    ax.add_patch(Rectangle((x,y+h-.07),w,.07,color=color,lw=0))
    if body:
        tx(ax,x+w/2,y+h-.40,title,fs,'bold',color,ha='center')
        tx(ax,x+w/2,y+(h-.5)/2,body,bodyfs,ha='center')
    else:tx(ax,x+w/2,y+h/2,title,fs,'bold',color,ha='center')
def arrow(ax,x1,y1,x2,y2,color=MUTED,dashed=False):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=17,lw=1.8,color=color,linestyle='--' if dashed else '-'))
def pill(ax,x,y,w,s,color=TEAL):
    ax.add_patch(FancyBboxPatch((x,y-.22),w,.45,boxstyle='round,pad=0.04,rounding_size=.15',facecolor=color,edgecolor='none'))
    tx(ax,x+w/2,y,s,12,'bold','white',ha='center')
def table(ax,x,y,w,h,headers,rows,widths=None,fs=14,highlights=()):
    # y is the top edge. Every row has explicit geometry; no automatic font shrinking.
    widths=np.array(widths or [1]*len(headers),float);widths=w*widths/widths.sum()
    rh=h/(len(rows)+1)
    cells=[]
    for i,vals in enumerate([headers]+list(rows)):
        yy=y-(i+1)*rh;xx=x
        for j,(value,ww) in enumerate(zip(vals,widths)):
            fill='#E0EDF1' if i==0 else ('#F3F7F9' if i%2==0 else 'white')
            if i-1 in highlights:fill='#E8F3F2'
            ax.add_patch(Rectangle((xx,yy),ww,rh,facecolor=fill,edgecolor=LINE,lw=.65))
            cells.append(tx(ax,xx+ww/2,yy+rh/2,str(value),fs,'bold' if i==0 else 'normal',ha='center'))
            xx+=ww
    return cells
def axplot(fig,bounds):
    ax=fig.add_axes(bounds);ax.set_axisbelow(True);ax.grid(axis='y');return ax
def data_csv(name,headers,rows):
    with (HERE/'data'/f'{name}.csv').open('w',encoding='utf-8-sig',newline='') as f:
        wr=csv.writer(f);wr.writerow(headers);wr.writerows(rows)
def save(code,title,fig,caption,group='main',data=None):
    fig.savefig(HERE/'png'/f'{code}.png',dpi=200)
    with plt.rc_context({'svg.fonttype':'path'}):fig.savefig(HERE/'svg'/f'{code}.svg')
    with plt.rc_context({'svg.fonttype':'none'}):fig.savefig(HERE/'svg_text'/f'{code}.svg')
    ASSETS.append({'id':code,'title':title,'group':group,'caption':caption,'data':data or [],'png':f'png/{code}.png','svg':f'svg/{code}.svg','editable_svg':f'svg_text/{code}.svg'})
    plt.close(fig)

def diagrams():
    fig,ax=base('01','암호화 통신의 첫 30패킷으로 서비스를 분류한다','모델 입력은 패킷 간격·방향·크기. 정답은 데이터셋의 서비스(APP) 라벨.','개념 그림의 숫자는 설명용 예시 · 채널 순서: IPT → DIR → SIZE · B는 플로우 배치 수')
    box(ax,.8,5.5,3.1,1.35,'암호화된 QUIC 플로우','양방향 통신의 패킷 순서',bodyfs=14)
    box(ax,4.65,5.5,4.0,1.35,'첫 최대 30패킷 관측','짧은 플로우도 포함 · 남는 칸은 0',bodyfs=14)
    box(ax,9.45,5.5,2.2,1.35,'분류 모델','M0–M5',color=BLUE)
    box(ax,12.45,5.5,2.75,1.35,'서비스 예측','고정된 C개 중 하나',color=PINK,bodyfs=14)
    for x1,x2 in [(3.95,4.60),(8.70,9.40),(11.70,12.40)]:arrow(ax,x1,6.18,x2,6.18)
    tx(ax,.9,4.75,'패킷별 관측값',19,'bold');pill(ax,12.1,4.75,3,'[B, 3, 30]')
    vals=[['IPT (ms)','0','8','3','20','0','0','…'],['DIR','+1','−1','−1','+1','0','0','…'],['SIZE (bytes)','1,200','90','1,350','80','0','0','…']]
    table(ax,.9,4.35,14.2,2.35,['채널','패킷 1','패킷 2','패킷 3','패킷 4','패딩','패딩','30칸까지'],vals,[1.5,1,1,1,1,1,1,1],fs=15)
    tx(ax,1.05,1.5,'사용하지 않는 예측 입력: payload · 도메인/SNI 문자열 · IP · 포트 · 전체 FLOWSTATS',15,color=MUTED)
    save('01_input','문제 정의와 PPI 입력',fig,'설명용 4패킷 플로우를 30칸으로 패딩한 예시. 실제 표본이나 실제 모델 예측은 아니다.')

    fig,ax=base('02','학습 후보는 정리하고, 평가는 자연 빈도를 유지한다','CESNET-QUICEXT-25-XS · 원본 1,000만 기록 · 실제 학습은 선택 서비스와 예산만 사용','4·5월은 프로젝트에서 이전에 확인한 시간차 평가 자료 · 완전히 새로운 외부 테스트셋은 아님')
    boxes=[('서비스·월 선택','혼합20 / 비Google13\nGoogle 계열20'),('유효성·입력 검사','8개 결함 해당 0건\nIPT·DIR·SIZE 계약'),('1월 후보 중복 정리','동일 입력·동일 라벨: 1개\n동일 입력·다른 라벨: 제외'),('균등·중첩 표본','서비스당 50⊂100⊂200⊂1,000\n같은 조건·seed는 같은 표본')]
    for i,(t,b) in enumerate(boxes):
        x=.8+i*3.75;box(ax,x,5.15,3.35,1.7,t,b,fs=16,bodyfs=13)
        if i<3:arrow(ax,x+3.4,6,x+3.7,6)
    tx(ax,.85,4.55,'2025년 자료의 역할',19,'bold')
    for x,t,b,c in [(1,'1월','학습 후보 정제\n모델 fitting',TEAL),(4.65,'2월','설정·학습률·KD 선택\nbest 체크포인트 선택',BLUE),(8.3,'4월','주평가\nAll + 겹침 분해',PINK),(11.95,'5월','시간차 재평가\n4월과 같은 고정 모델',PURPLE)]:box(ax,x,2.4,3.05,1.6,t,b,color=c)
    tx(ax,8,1.75,'3월 미사용  |  2·4·5월 정답으로 1월 후보를 정제하지 않음',14,ha='center')
    tx(ax,8,1.22,'평가 All의 반복·불균형은 보존하고, 학습 겹침·비겹침·공통 미노출을 별도 집계',14,ha='center')
    save('02_data_protocol','데이터 처리와 시간 분할',fig,'1월 학습 후보만 중복·충돌을 정리했다. 서비스 자격은 1월 정제 후 고유 입력 1,000개 이상을 기준으로 확정했다.')

    fig,ax=base('03','M0–M5는 구조·사전학습·학습 신호를 비교한다','모델 종류는 6개. 조건과 seed를 달리해 학습한 결과물은 180개.','M1↔M2는 선택 학습률·BN 통계 정책도 다름 · 사전학습 가중치만의 단일 요인 효과로 해석하지 않음')
    rows=[['M0','16개 PPI 통계 → LightGBM','미사용','정답','전통적 기준선'],['M1','큰 잔차 CNN 교사','미사용','정답 CE','직접학습 교사'],['M2','M1과 동일한 교사 구조','공개 가중치 사용','정답 CE · 전체 미세조정','사전학습 활용'],['M3','작은 3층 CNN 학생','미사용','정답 CE','증류 없는 학생'],['M4','M3와 동일한 학생 구조','미사용','정답 CE + M1 확률 KL','직접학습 교사 증류'],['M5','M3와 동일한 학생 구조','미사용','정답 CE + M2 확률 KL','사전학습 교사 증류']]
    table(ax,.8,6.95,14.4,4.5,['모델','구조','사전학습 가중치','학습 신호','비교 역할'],rows,[.6,2,1.35,2,1.4],fs=14,highlights=[2,5])
    tx(ax,8,1.82,'6조건 × 5 seed × 6모델 = 180회 학습',21,'bold',TEAL,ha='center')
    tx(ax,8,1.23,'180개 모델 × 4·5월 = 360건 평가   |   학습된 180개 모델 각각 CPU 추론 벤치마크',15,ha='center')
    data_csv('03_model_map',['model','architecture','pretrained_weights','signal','role'],rows)
    save('03_model_map','M0–M5 실험 비교표',fig,'신경망은 A100 학습, M0는 CPU 학습. CPU 비용 측정은 학습된 모델의 추론 벤치마크다.',data=['03_model_map.csv'])

    fig,ax=base('04','같은 30패킷을 받아도 내부 표현과 모델 용량은 다르다','C=20 기준 · M1/M2는 교사 구조를 공유하고, M3/M4/M5는 학생 구조를 공유한다','pooling 전 최대 국소 수용영역: 교사 19패킷 / 학생 7패킷 · 구조에서 계산한 차이이며 성능 격차의 원인으로 입증한 것은 아님')
    pill(ax,.8,6.9,3.2,'교사 · M1 / M2',TEAL);pill(ax,8.3,6.9,3.2,'학생 · M3 / M4 / M5',PINK)
    teacher=[('PPI [B,3,30]','처음 최대 30패킷'),('패킷 임베딩 [B,32,30]','SIZE 20 + IPT 10 + DIR 2'),('잔차 CNN 4블록','32 → 192 → 256 → 384 → 448'),('GeM pooling → Linear','448차원 → C개 서비스')]
    student=[('PPI [B,3,30]','처음 최대 30패킷'),('고정 변환 + 유효 마스크','IPT log-scale / SIZE scale / DIR'),('일반 CNN 3층','3 → 32 → 64 → 64'),('Masked mean → Linear','64차원 → C개 서비스')]
    for xx,items,col in [(1,teacher,TEAL),(8.5,student,PINK)]:
        for i,(t,b) in enumerate(items):
            y=5.55-i*1.12;box(ax,xx,y,6.4,.88,t,b,color=col,fs=15,bodyfs=12)
            if i<3:arrow(ax,xx+3.2,y-.02,xx+3.2,y-.22,color=col)
    tx(ax,4.2,1.45,'695,593 parameters',21,'bold',TEAL,ha='center')
    tx(ax,11.7,1.45,'20,180 parameters',21,'bold',PINK,ha='center')
    save('04_architecture','교사와 학생 구조 요약',fig,'교사는 공개 30pktTCNET backbone을 활용하되 pooled 448차원에 새 분류기를 연결했다. 256차원 wrapper 출력 경로가 아니다.')

    fig,ax=base('04D','실제 구현 기준의 텐서 크기와 연산','B=배치 크기 · C=목표 서비스 수 · 모든 CNN의 패킷 축 stride=1','공개 256차원 wrapper 후단은 사용하지 않음 · M2의 BN running 통계 고정, affine 계수는 학습')
    tr=[['입력','[B,3,30]','IPT_ms / DIR / SIZE_bytes'],['임베딩','[B,32,30]','SIZE 1501×20 · IPT 200×10 · DIR 2'],['잔차 블록 1','[B,192,30]','중간 48 · kernel 7'],['잔차 블록 2','[B,256,30]','중간 64 · kernel 7'],['잔차 블록 3','[B,384,30]','중간 96 · kernel 5'],['잔차 블록 4','[B,448,30]','중간 112 · kernel 3'],['GeM → Linear','[B,448] → [B,C]','학습 가능한 pooling + 새 head']]
    sr=[['입력·변환','[B,3,30]','IPT log 정규화 / SIZE÷1500 / DIR'],['Conv1d 1','[B,32,30]','kernel 3 · padding 1 · ReLU'],['Conv1d 2','[B,64,30]','kernel 3 · padding 1 · ReLU'],['Conv1d 3','[B,64,30]','kernel 3 · padding 1 · ReLU'],['다시 마스킹','각 합성곱 직후','DIR≠0인 위치만 유지'],['Masked mean','[B,64]','유효 위치 수로 나눔'],['Linear','[B,C]','64 → C']]
    tx(ax,4.35,6.92,'교사 · M1/M2',18,'bold',TEAL,ha='center');tx(ax,11.65,6.92,'학생 · M3/M4/M5',18,'bold',PINK,ha='center')
    table(ax,.7,6.55,7.05,4.7,['단계','출력','연산'],tr,[1,1.15,2],fs=11.8)
    table(ax,8.05,6.55,7.25,4.7,['단계','출력','연산'],sr,[1,1.05,2.05],fs=11.8)
    tx(ax,.9,1.46,'교사 블록: 1×1 축소 → 중앙 Conv → 1×1 확장 + skip projection  |  학생: BN·dropout·residual 없음',12.5)
    tx(ax,.9,1.02,'학생 IPT 변환: log1p(clip(IPT_ms, 0, 65000)) / log1p(65000)  |  SIZE는 유효 패킷에서 1–1500으로 clip',12.5)
    save('04D_architecture_detail','모델 구조 상세',fig,'실제 코드 및 architecture snapshot 기준. 교사의 임베딩·pooling과 학생의 고정 변환·마스킹은 서로 다르다.','backup')

    fig,ax=base('05','교사의 확률 분포로 학생을 학습하고, 추론은 학생만 한다','M4의 교사는 M1 · M5의 교사는 M2 · 같은 구성·예산·seed의 교사를 연결','α=0.5, T=1 · 교사 분포는 학습 손실에만 사용 · 학생 입력 채널에 정답이나 교사 확률을 붙이지 않음')
    pill(ax,.85,6.88,2.3,'학습 단계',TEAL)
    box(ax,1,3.75,2.3,1.25,'동일한 PPI','학습 입력',bodyfs=14)
    box(ax,4.15,5.25,3.2,1.05,'학습된 교사','고정 · 확률 분포 생성',color=TEAL,bodyfs=13)
    box(ax,4.15,3.6,3.2,1.05,'학습 중인 학생','서비스별 logits',color=PINK,bodyfs=13)
    box(ax,8.25,5.25,3.1,1.05,'교사 분포 KL','학생이 분포를 따르도록',color=TEAL,bodyfs=13)
    box(ax,8.25,3.6,3.1,1.05,'정답 CE','실제 라벨을 맞히도록',color=PINK,bodyfs=13)
    box(ax,12.25,4.4,2.8,1.15,'학생 가중치 갱신','두 손실을 결합',color=BLUE,bodyfs=13)
    arrow(ax,3.3,4.7,4.13,5.7);arrow(ax,3.3,4.2,4.13,4.1)
    arrow(ax,7.38,5.78,8.22,5.78,TEAL);arrow(ax,7.38,4.15,8.22,4.15,PINK)
    arrow(ax,7.35,4.55,8.25,5.4,PINK);arrow(ax,11.38,5.78,12.22,5.2);arrow(ax,11.38,4.15,12.22,4.7)
    tx(ax,9.78,3.02,'정답 y → CE',14,color=PINK,ha='center')
    tx(ax,8,2.4,'L = (1−α)·CE + α·T²·KL(교사 ∥ 학생)',22,'bold',ha='center')
    pill(ax,.85,1.55,2.3,'배포·추론',PINK)
    tx(ax,4.15,1.55,'새 PPI',18,'bold');arrow(ax,5.6,1.55,6.8,1.55)
    tx(ax,7.0,1.55,'학생만 실행',18,'bold',PINK);arrow(ax,9,1.55,10.2,1.55);tx(ax,10.5,1.55,'서비스 예측',18,'bold')
    save('05_distillation','지식 증류 학습과 추론',fig,'교사는 학습 중 동결한다. 교사 logits는 동일 fitting 입력에서 미리 계산해 재사용했다. T=1이어도 전체 분포를 따르는 KL이 남는다.')

def results():
    footer='혼합20 · 서비스당 200개 · 2025년 4월 All · 5 seed 평균 ± 표본 SD · SD는 신뢰구간/유의성 검정이 아님'
    fig,bg=base('06','사전학습 교사는 유리했지만, 학생의 성능 유지에는 한계가 있다','대표 조건의 M0–M5 비교 · 주지표 Macro-F1',footer)
    ax=axplot(fig,[.075,.20,.62,.56]);y=[100*row('mixed_n200',m)['macro_f1']['mean'] for m in MODELS];sd=[100*row('mixed_n200',m)['macro_f1']['sd'] for m in MODELS]
    ax.bar(np.arange(6),y,yerr=sd,color=[COLORS[m] for m in MODELS],width=.62,capsize=5)
    for i,(v,e) in enumerate(zip(y,sd)):ax.text(i,v+e+1.5,f'{v:.2f}',ha='center',fontsize=17,weight='bold')
    ax.set(xticks=range(6),xticklabels=[m+'\n'+LABELS[m] for m in MODELS],ylim=(0,65),ylabel='Macro-F1 (%)');ax.tick_params(axis='x',labelsize=12)
    for y0,t,b,c in [(5.8,'M2 − M1',f"+{pair('mixed_n200','M2−M1')['mean_pp']:.2f}%p\n사전학습 활용의 평균 차이",TEAL),(4.0,'M5 − M3',f"+{pair('mixed_n200','M5−M3')['mean_pp']:.2f}%p\n증류 학생의 작은 평균 개선",PINK),(2.2,'M2 − M5',f"{pair('mixed_n200','M2−M5')['mean_pp']:.2f}%p\n학생에 남은 성능 격차",BLUE)]:box(bg,11.65,y0-1.05,3.55,1.45,t,b,color=c,fs=17,bodyfs=14)
    save('06_main_performance','대표 조건 성능 그래프',fig,'막대 높이는 Macro-F1의 5개 seed 평균. M2−M1에는 초기값 외 선택 학습률·BN 정책 차이도 포함된다.')

    fig,bg=base('06T','대표 조건의 수치 결과: 4월 주평가와 5월 재평가','같은 학습 모델을 두 달에 각각 평가 · 표의 단위는 %', '혼합20 · 서비스당 200개 · 5 seed 평균 ± 표본 SD · CE/KL 개발 선택 결과와 구분')
    rr=[];csvrows=[]
    for m in MODELS:
        vals=[]
        for month in ['202504','202505']:
            r=row('mixed_n200',m,month)
            vals += [f"{r[k]['mean']*100:.2f} ± {r[k]['sd']*100:.2f}" for k in ['macro_f1','accuracy']]
            csvrows.append([m,month]+[r[k][q] for k in ['macro_f1','accuracy'] for q in ['mean','sd']])
        rr.append([m,LABELS[m]]+vals)
    table(bg,.8,6.9,14.4,4.65,['모델','역할','4월 Macro-F1','4월 Accuracy','5월 Macro-F1','5월 Accuracy'],rr,[.55,1.55,1.5,1.5,1.5,1.5],fs=14,highlights=[2,5])
    tx(bg,8,1.55,'Accuracy와 Macro-F1을 함께 보고, 서비스별 불균형은 Macro-F1로 보완',17,'bold',ha='center')
    data_csv('06_representative',['model','month','macro_f1_mean','macro_f1_sd','accuracy_mean','accuracy_sd'],csvrows)
    save('06T_main_results','대표 성능 결과표',fig,'표의 ±는 표본 표준편차. 모델 선택은 2월 검증에서 수행했으며 4·5월은 동결 모델의 평가다.',data=['06_representative.csv'])

    fig,bg=base('07','라벨을 늘렸을 때의 성능 증가가 증류의 추가 이득보다 컸다','혼합20 · 서비스당 50 / 100 / 200 / 1,000개 · 4월 All','동일 seed에서 50⊂100⊂200⊂1,000 · 5 seed 평균 ± SD · 예산별 업데이트 횟수는 다름')
    ax=axplot(fig,[.08,.22,.60,.51]);budgets=[50,100,200,1000]
    for m in MODELS:
        v=[row(f'mixed_n{b}',m)['macro_f1'] for b in budgets]
        ax.errorbar(budgets,[z['mean']*100 for z in v],yerr=[z['sd']*100 for z in v],color=COLORS[m],label=m,marker='o',capsize=4,lw=2.4 if m in ['M2','M5'] else 1.6,linestyle='-' if m in ['M2','M5'] else '--')
    ax.set(xscale='log',xlim=(40,1250),ylim=(0,70),ylabel='Macro-F1 (%)',xlabel='서비스당 학습 라벨 수 (로그축)')
    ax.set_xticks(budgets,[str(b) for b in budgets]);ax.xaxis.set_minor_locator(NullLocator());ax.legend(ncol=6,frameon=False,loc='upper left',bbox_to_anchor=(0,1.15))
    gain=100*(row('mixed_n1000','M5')['macro_f1']['mean']-row('mixed_n50','M5')['macro_f1']['mean'])
    box(bg,11.65,4.75,3.55,1.45,'M5 · 50 → 1,000',f'+{gain:.2f}%p',color=PINK,fs=17,bodyfs=24)
    box(bg,11.65,2.7,3.55,1.45,'M5 − M3', '예산별 약 +0.24~0.39%p',color=TEAL,fs=17,bodyfs=14)
    save('07_label_budget','라벨 예산별 성능 곡선',fig,'평균 성능의 기술적 비교다. 모든 예산에서 동일 50 epoch를 사용하므로 라벨 증가와 연산량 증가를 분리한 실험은 아니다.')

    fig,bg=base('08','Google 내부 구분이 어렵지만, 학생의 격차는 다른 구성에도 남는다','서비스당 200개 · 4월 All · 비교를 읽기 쉽게 M2/M3/M5를 강조','5 seed 평균 ± SD · 서비스 수와 경쟁 클래스가 다르므로 Google 여부 하나의 인과효과가 아님')
    ax=axplot(fig,[.08,.27,.84,.46]);xx=np.arange(3)
    for i,m in enumerate(['M2','M3','M5']):
        v=[row(s,m)['macro_f1'] for s in COHORTS];yy=[q['mean']*100 for q in v];ee=[q['sd']*100 for q in v]
        ax.bar(xx+(i-1)*.23,yy,width=.21,yerr=ee,capsize=4,color=COLORS[m],label=m+' '+LABELS[m])
        for x,y,e in zip(xx+(i-1)*.23,yy,ee):ax.text(x,y+e+1.4,f'{y:.1f}',ha='center',fontsize=14,weight='bold')
    ax.set(xticks=xx,xticklabels=['혼합20','비Google13','Google 계열20'],ylim=(0,100),ylabel='Macro-F1 (%)');ax.legend(ncol=3,frameon=False,loc='upper center',bbox_to_anchor=(.5,1.17))
    tx(bg,8,1.55,'비Google13에도 Meta 서비스가 포함됨 · Meta 전용 학습 실험을 수행한 것은 아님',15,ha='center')
    save('08_service_cohorts','서비스 구성별 성능',fig,'본문용으로 M2/M3/M5만 강조했다. 6개 모델의 모든 조건별 결과는 데이터 CSV와 기존 보고서에 보존되어 있다.')

    fig,bg=base('10','학생은 가볍고 빠르지만, 교사의 분류 성능은 유지하지 못했다','대표 혼합20·200개 · 세로축은 4월 성능, 가로축은 CPU 추론 시간','Apple M5 · CPU 1 thread · FP32 · batch 1 median의 seed 평균 · 수집·패킷 대기·전체 전처리 비용 제외')
    ax=axplot(fig,[.08,.23,.58,.51]);offset={'M0':(8,-20),'M1':(8,-18),'M2':(8,8),'M3':(-45,-26),'M4':(16,-2),'M5':(-45,18)}
    for m in MODELS:
        x=cost('mixed_n200',m)['batch1_median_ms']['mean'];r=row('mixed_n200',m);y=r['macro_f1']['mean']*100
        ax.scatter(x,y,s=160,color=COLORS[m],edgecolor='white',zorder=3);ax.errorbar(x,y,yerr=r['macro_f1']['sd']*100,color=COLORS[m],capsize=4)
        ax.annotate(m,(x,y),xytext=offset[m],textcoords='offset points',fontsize=15,weight='bold',color=COLORS[m],arrowprops={'arrowstyle':'-','color':COLORS[m],'lw':.8})
    ax.set(xscale='log',xlim=(.025,.65),ylim=(0,65),xlabel='CPU 추론 지연 (ms, 로그축) · 왼쪽이 빠름',ylabel='Macro-F1 (%) · 위쪽이 높음')
    ticks=[.03,.04,.06,.1,.2,.3,.5];ax.set_xticks(ticks,[str(t) for t in ticks]);ax.xaxis.set_minor_locator(NullLocator());ax.grid(axis='x',which='major')
    ct=cost('mixed_n200','M2');cs=cost('mixed_n200','M5')
    rows=[['파라미터',f"{ct['parameters']:,}",f"{cs['parameters']:,}"],['지연 (ms)',f"{ct['batch1_median_ms']['mean']:.4f}",f"{cs['batch1_median_ms']['mean']:.4f}"],['추론파일 (MiB)',f"{ct['inference_MiB']['mean']:.3f}",f"{cs['inference_MiB']['mean']:.3f}"],['Macro-F1 (%)',f"{row('mixed_n200','M2')['macro_f1']['mean']*100:.2f}",f"{row('mixed_n200','M5')['macro_f1']['mean']*100:.2f}"]]
    table(bg,11.3,6.3,3.9,2.9,['항목','M2','M5'],rows,[1.5,1,1],fs=12)
    tx(bg,13.25,2.6,f"파라미터 {ct['parameters']/cs['parameters']:.2f}배 감소\n지연 {ct['batch1_median_ms']['mean']/cs['batch1_median_ms']['mean']:.2f}배 단축",17,'bold',TEAL,ha='center')
    save('10_accuracy_cost','성능과 CPU 추론 비용',fig,'SD는 세로축 F1 변동만 표시한다. 개별 seed의 latency median을 평균했으며 통합 측정 중앙값이 아니다. 파라미터 감소는 메모리 RSS 감소와 같지 않다.')

def full_confusion(stage,model,month='202504'):
    reg=E/'continuation_recovered'/stage/'evaluation_registry.json'
    r=source(reg);v=source(ROOT/r['verification'])
    records=[x for x in v['records'] if x['model']==model and x['month']==month]
    assert sorted(x['seed'] for x in records)==[201,202,203,204,205]
    classes=records[0]['classes'];cms=np.array([x['groups']['all']['confusion'] for x in records],dtype=np.int64)
    support=np.array(records[0]['groups']['all']['support'])
    assert np.all(cms.sum(2)==support[None,:])
    csum=cms.sum(0);rate=100*csum/(5*support[:,None])
    assert np.allclose(rate.sum(1),100)
    # Validate against the already reported top pairs (avoids interpreting missing top pairs as zero).
    rr=next(r for r in S['confusions'] if (r['stage'],r['month'],r['model'])==(stage,month,model))
    for p in rr['pairs']:assert csum[classes.index(p['true']),classes.index(p['predicted'])]==p['count']
    data_csv(f'09_{stage}_{model}_full',['true_service','support_per_seed']+classes,[[c,int(support[i])]+list(rate[i]) for i,c in enumerate(classes)])
    CHECKS.append(f'{stage} {model}: 5 confusion matrices, row supports, 100% totals and saved top pairs agree')
    return classes,rate,support

def heat(ax,mat,labels,cols,title,fontsize=10,full=False):
    im=ax.imshow(mat,vmin=0,vmax=100,cmap='YlGnBu',aspect='auto')
    ax.set_xticks(range(len(cols)),cols,rotation=38,ha='right',fontsize=fontsize)
    ax.set_yticks(range(len(labels)),labels,fontsize=fontsize)
    ax.tick_params(length=0);ax.set_title(title,fontsize=15,fontweight='bold',pad=13)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            if not full or mat[i,j]>=5 or i==j:
                ax.text(j,i,f'{mat[i,j]:.1f}',ha='center',va='center',fontsize=fontsize if not full else 9,color='white' if mat[i,j]>52 else INK)
    return im

def confusion_figures():
    gd=['google-www','google-ads','google-usercontent','google-calendar','youtube','firebase-crashlytics']
    md=['facebook-graph','instagram','facebook-media','facebook-web','whatsapp','facebook-connect']
    short={'google-www':'WWW','google-ads':'Ads','google-usercontent':'Usercontent','google-calendar':'Calendar','youtube':'YouTube','firebase-crashlytics':'Crashlytics','facebook-graph':'FB Graph','instagram':'Instagram','facebook-media':'FB Media','facebook-web':'FB Web','whatsapp':'WhatsApp','facebook-connect':'FB Connect'}
    matrices={}
    for stage in ['googleonly_n200','nongoogle_n200']:
        for model in ['M2','M5']:matrices[(stage,model)]=full_confusion(stage,model)
    fig,bg=base('09','Google·Meta 내부 혼동은 학생에서 더 커지는 경우가 있다','실제 서비스별 예측 비율 (%) · 같은 척도 0–100 · 행=실제, 열=예측','서비스당 200개 · 4월 All · 5 seed 평균 · 선택하지 않은 예측 클래스는 ‘기타’로 합산하여 행 합계 100% 유지')
    positions=[(.115,.535,.32,.215),(.59,.535,.32,.215),(.115,.165,.32,.235),(.59,.165,.32,.235)]
    for i,(stage,model,selected) in enumerate([('googleonly_n200','M2',gd),('googleonly_n200','M5',gd),('nongoogle_n200','M2',md),('nongoogle_n200','M5',md)]):
        cls,rate,sup=matrices[(stage,model)];idx=[cls.index(x) for x in selected];other=[j for j in range(len(cls)) if j not in idx]
        mat=np.column_stack([rate[np.ix_(idx,idx)],rate[np.ix_(idx,other)].sum(1)])
        assert np.allclose(mat.sum(1),100)
        ax=fig.add_axes(positions[i]);lab=[short[c] for c in selected]
        im=heat(ax,mat,lab,lab+['기타'],('Google 계열20 중 선택 서비스' if stage=='googleonly_n200' else '비Google13 중 Meta 서비스')+f' · {model}',9.5)
        data_csv(f'09_{stage}_{model}_focused',['true_service','support_per_seed']+selected+['other'],[[c,int(sup[idx[k]])]+list(mat[k]) for k,c in enumerate(selected)])
    cb=fig.colorbar(im,cax=fig.add_axes([.94,.21,.012,.49]));cb.ax.tick_params(labelsize=10);cb.set_label('예측 비율 (%)',fontsize=11)
    save('09_confusion_focus','Google·Meta 혼동 비교',fig,'Google의 6개 서비스는 주요 혼동을 설명하기 위한 부분집합이다. Meta는 비Google13 실험에서 6개 관련 서비스를 뽑은 것이며 Meta 전용 실험이 아니다. 다른 예측 클래스는 기타 열에 보존했다.',data=[f'09_{s}_{m}_focused.csv' for s in ['googleonly_n200','nongoogle_n200'] for m in ['M2','M5']])
    for model in ['M2','M5']:
        cls,mat,sup=matrices[('googleonly_n200',model)]
        labels=[c.replace('google-','').replace('firebase-','') for c in cls]
        fig,bg=base('09'+model,'Google 계열20 전체 혼동행렬 · '+model,LABELS[model]+' · 행=실제 서비스 / 열=예측 서비스 · 비율(%)','서비스당 200개 · 4월 All · 5 seed 평균 · 대각선 및 5% 이상만 숫자 표시 · 모든 셀 값은 동봉 CSV에 보존')
        ax=fig.add_axes([.16,.24,.72,.51]);im=heat(ax,mat,labels,labels,'',10,True)
        fig.colorbar(im,cax=fig.add_axes([.90,.24,.015,.51])).set_label('예측 비율 (%)')
        save(f'09D_google_{model}',f'Google 전체 혼동행렬 {model}',fig,'20개 전체 클래스의 행 정규화 혼동행렬. 숫자 미표시 셀은 0이라는 뜻이 아니다.','backup',data=[f'09_googleonly_n200_{model}_full.csv'])

def supplements():
    fig,bg=base('03B','실제로 수행한 실험은 6조건 × 5 seed × 6모델이다','혼합20에서 라벨 수를 비교하고, 나머지 두 구성에서는 200개 조건을 비교','개발 60회는 설정 선택용이며 본실험 180회와 별도 · 서비스당 1,000개 자격은 1월 정제 후 후보 수 기준')
    table(bg,1,6.85,14,3.45,['서비스 구성','50개','100개','200개','1,000개','학습 합계'],[['혼합20','30회','30회','30회','30회','120회'],['비Google13','—','—','30회','—','30회'],['Google 계열20','—','—','30회','—','30회']],[1.8,1,1,1,1,1.2],fs=18)
    for x,t,b,c in [(1.1,'180개 학습 모델','6조건 × 5 seed × M0–M5',TEAL),(6.05,'360건 월간 평가','180개 × 4월·5월',BLUE),(11,'180개 CPU 벤치마크','각 모델 내부에서 반복 측정',PINK)]:box(bg,x,1.4,3.9,1.45,t,b,color=c,fs=19,bodyfs=14)
    save('03B_experiment_matrix','실험 행렬과 실행 수',fig,'빈 칸은 미실행 조건이다. 3개 구성 × 4개 예산의 모든 조합을 실행한 것은 아니다.','backup')

    audit=ROOT/'experiments/2026-10-28_data_audit/clipped_summary.csv'
    SOURCES[str(audit.relative_to(ROOT))]=hashlib.sha256(audit.read_bytes()).hexdigest()
    with audit.open() as f:rr=[r for r in csv.DictReader(f) if r['cohort']=='google_included20' and r['period']=='202501' and r['policy']=='padded']
    rr.sort(key=lambda r:int(r['packets']));assert len(rr)==30
    fig,bg=base('B01','관측 길이가 늘면 정확히 같은 입력의 라벨 충돌이 줄어든다','혼합20 · 1월 · 정규화 PPI · 짧은 플로우도 패딩하여 같은 분모 사용','충돌률은 모델 오분류율이 아님 · 30패킷의 정확한 충돌 감소가 서비스 간 패턴 분리를 보장하지 않음')
    ax=axplot(fig,[.08,.24,.57,.50]);xx=[int(r['packets']) for r in rr];yy=[100*float(r['conflicting_rate']) for r in rr]
    ax.plot(xx,yy,color=TEAL,lw=2.5,marker='o',ms=5);ax.set(xlim=(1,30),ylim=(0,100),xticks=[1,2,5,10,20,30],xlabel='첫 k개 패킷',ylabel='충돌 기록 비율 (%)')
    pick=[r for r in rr if int(r['packets']) in [1,2,5,10,20,30]]
    table(bg,11,6.55,4.2,3.85,['k','충돌 기록','비율 (%)'],[[r['packets'],f"{int(r['conflicting_rows']):,}",f"{float(r['conflicting_rate'])*100:.4f}"] for r in pick],[.5,1.4,1.2],fs=14)
    tx(bg,12.9,1.9,'학습 후보 정제는\n실제 사용하는 30-PPI 기준',14,'bold',ha='center')
    data_csv('B01_collision',list(rr[0]),[list(r.values()) for r in rr]);save('B01_collision','입력 길이별 충돌',fig,'정규화된 순서 있는 입력이 완전히 같고 라벨이 다른 그룹의 기록 비율. 최소 가능 오류율과 다르다.','backup',data=['B01_collision.csv'])

    fig,bg=base('B02','학습 입력 재등장을 제외해도 대표 경향은 거의 같다','M5 · 서비스당 200개 · 4월 · All / 현재 학습 비겹침 / 공통 미노출','5 seed 평균 · 공통 미노출은 개발·본실험 최대 예산·검증 입력 합집합과 비겹침 · 작은 겹침 집합의 F1은 일반화하지 않음')
    ax=axplot(fig,[.08,.39,.84,.34]);xx=np.arange(3);groups=['all','train_nonoverlap','common_unseen'];gl=['All','현재 학습 비겹침','공통 미노출'];gc=['#A7BAC4',TEAL,PINK]
    for j,g in enumerate(groups):
        yy=[row(s,'M5',group=g)['macro_f1']['mean']*100 for s in COHORTS];ax.bar(xx+(j-1)*.24,yy,width=.22,label=gl[j],color=gc[j])
        for x,y in zip(xx+(j-1)*.24,yy):ax.text(x,y+1,f'{y:.2f}',ha='center',fontsize=12)
    ax.set(xticks=xx,xticklabels=list(COHORTS.values()),ylim=(0,60),ylabel='Macro-F1 (%)');ax.legend(ncol=3,frameon=False,loc='upper center',bbox_to_anchor=(.5,1.22))
    tab=[]
    for s,label in COHORTS.items():
        ro=row(s,'M5',group='train_overlap');un=row(s,'M5',group='common_unseen');a=row(s,'M5')
        tab.append([label,f"{a['n'][0]:,}",'/'.join(map(str,ro['n'])),f"{un['n'][0]:,}"])
    table(bg,1.3,3.0,13.4,1.75,['구성','All N','학습 겹침 N (seed 201→205)','공통 미노출 N'],tab,[1.2,1.2,2.5,1.4],fs=13)
    save('B02_overlap','평가 겹침과 비겹침',fig,'겹침은 source ID가 아니라 정규화된 PPI 값의 정확한 일치다. 작은 overlap 집합은 빈 클래스가 많아 전체적인 능력의 지표로 사용하지 않는다.','backup')

    fig,bg=base('B03','50 epoch의 진행과 모델별 검증 성능을 함께 확인한다','혼합20 · 본실험의 2월 검증 · 실선=5 seed 평균 / 음영=±표본 SD','best 체크포인트는 각 seed의 검증 점수로 선택 · 평균곡선 최고점과 선택 epoch는 같을 필요가 없음')
    for j,stage in enumerate(['mixed_n50','mixed_n200']):
        ax=axplot(fig,[.075+j*.47,.25,.40,.46])
        for m in MODELS[1:]:
            records=[r for r in D['main_training'] if r['stage']==stage and r['model']==m]
            arr=np.array([[h['validation']['macro_f1']*100 for h in r['history_compact']] for r in records]);assert arr.shape==(5,50)
            avg=arr.mean(0);sd=arr.std(0,ddof=1);ax.plot(range(1,51),avg,color=COLORS[m],label=m,lw=2);ax.fill_between(range(1,51),avg-sd,avg+sd,color=COLORS[m],alpha=.12)
        ax.set(title='서비스당 '+('50개' if j==0 else '200개'),xlabel='Epoch',ylabel='검증 Macro-F1 (%)' if j==0 else '',ylim=(0,80),xlim=(1,50));ax.legend(ncol=5,frameon=False,fontsize=12,loc='lower right')
    tx(bg,8,1.4,'같은 50 epoch도 예산별 업데이트 수가 다르다 · 일부 50개 조건은 마지막 epoch가 best',16,ha='center')
    save('B03_validation_curves','검증 학습곡선',fig,'저장된 본실험 50 epoch 기록에서 직접 계산. 수렴이 충분했다는 보장이나 추가 학습 결과가 아니다.','backup')

    fig,bg=base('B03L','학습 손실과 검증 손실은 모델별로 따로 읽는다','혼합20 · 서비스당 200개 · 같은 정답 CE를 쓰는 M2와 M3의 예시','학습 손실은 batch 평균의 단순평균, 검증 CE는 전체 표본 기준 · M4/M5의 CE+KL 혼합손실과 직접 비교하지 않음')
    for j,m in enumerate(['M2','M3']):
        ax=axplot(fig,[.075+j*.47,.24,.40,.48]);records=[r for r in D['main_training'] if r['stage']=='mixed_n200' and r['model']==m]
        for name,func,ls in [('학습 CE',lambda h:h['train_loss'],'-'),('검증 CE',lambda h:h['validation']['gt_cross_entropy'],'--')]:
            ar=np.array([[func(h) for h in r['history_compact']] for r in records]);avg=ar.mean(0);sd=ar.std(0,ddof=1)
            ax.plot(range(1,51),avg,label=name,color=COLORS[m],linestyle=ls,lw=2.5);ax.fill_between(range(1,51),avg-sd,avg+sd,color=COLORS[m],alpha=.09)
        ax.set(title=m+' '+LABELS[m],xlabel='Epoch',ylabel='정답 cross-entropy' if j==0 else '',ylim=(0,4),xlim=(1,50));ax.legend(frameon=False)
    tx(bg,8,1.35,'실선·점선은 5 seed 평균, 음영은 ±표본 SD · 검증 손실과 검증 F1을 함께 확인',15,ha='center')
    save('B03L_train_validation_loss','학습과 검증 손실',fig,'M3와 M5의 train_loss는 서로 다른 목적함수라서 같은 종류의 손실로 겹쳐 비교하지 않았다.','backup')

    sel=D['development_selection'];fig,bg=base('B04','설정은 2월 검증에서 선택하고 본실험에서 고정했다','개발 seed 101·102 · 대표 혼합20·200개 · 개발 60회는 성능 본실험과 별도','KD: 두 교사 × 두 seed의 학생 4개 평균 · 최종 α=0.5, T=1 · 다른 예산과 서비스 구성에서 재탐색하지 않음')
    tab=[]
    for m in ['M0','M1','M2','M3']:
        rs=sel['lr_comparisons'][m]
        for r in rs:tab.append([m,str(r['candidate']),f"{r['mean_macro_f1']*100:.2f}",'선택' if r['candidate']==sel['selected'][m] else ''])
    table(bg,.8,6.8,7.0,5.45,['모델','후보 (LR / leaves)','검증 F1 (%)','결정'],tab,[.7,1.65,1.2,.7],fs=12.5,highlights=[2,5,8,11])
    ax=fig.add_axes([.58,.32,.31,.36]);ar=np.array([[next(r['mean_macro_f1']*100 for r in sel['kd_grid'] if r['alpha']==a and r['temperature']==t) for t in [1,2,4]] for a in [.1,.25,.5]])
    im=ax.imshow(ar,vmin=39,vmax=45,cmap='YlGnBu');ax.set(xticks=range(3),xticklabels=[1,2,4],yticks=range(3),yticklabels=[.1,.25,.5],xlabel='온도 T',ylabel='α',title='공통 KD 후보 · 검증 Macro-F1 (%)');ax.tick_params(length=0)
    for i in range(3):
        for j in range(3):ax.text(j,i,f'{ar[i,j]:.2f}',ha='center',va='center',color='white' if ar[i,j]>43 else INK,fontsize=18)
    ax.add_patch(Rectangle((-.5,1.5),1,1,fill=False,ec=GOLD,lw=4));tx(bg,11.75,1.7,'최고 평균: 44.52%\n후보 간 작은 차이를 보편적 최적으로 해석하지 않음',14,ha='center')
    data_csv('B04_kd_grid',['alpha','T','mean_validation_macro_f1'],[[r['alpha'],r['temperature'],r['mean_macro_f1']] for r in sel['kd_grid']]);save('B04_selection','설정 선택 근거',fig,'LR/leaves는 개발 seed 2개 평균, KD는 교사 2개×seed 2개 평균이다. 최적값의 통계적 확실성을 입증한 실험은 아니다.','backup',data=['B04_kd_grid.csv'])

    for index,(stage,label) in enumerate(COHORTS.items(),1):
        fig,bg=base(f'B05-{index}',label+'의 서비스별 성능과 평가 표본 수','서비스당 200개 학습 · 4월 All · M2와 M5의 5 seed 평균 · P=정밀도 / R=재현율 / F1','각 seed의 P/R/F1을 각각 평균 · 평균 P와 R에 F1 공식을 다시 적용한 값이 아님 · 단위 %')
        rows=[]
        for r in S['class_rows']:
            if r['stage']==stage and r['month']=='202504':
                rows.append([r['service'],f"{r['support']:,}"]+[f"{r['models'][m][k]*100:.1f}" for m in ['M2','M5'] for k in ['per_class_precision','per_class_recall','per_class_f1']])
        table(bg,.75,7,14.5,5.9,['실제 서비스','N','M2 P','M2 R','M2 F1','M5 P','M5 R','M5 F1'],rows,[2.8,1.15,.9,.9,.9,.9,.9,.9],fs=12 if len(rows)>15 else 14)
        data_csv(f'B05_{stage}', ['service','support','M2_precision_pct','M2_recall_pct','M2_f1_pct','M5_precision_pct','M5_recall_pct','M5_f1_pct'],rows)
        save(f'B05_{stage}',label+' 서비스별 결과표',fig,'드문 서비스는 support와 함께 읽는다. 전체 M0–M5·4/5월의 정확한 평균 수치는 all_class_results.csv에 제공한다.','backup',data=[f'B05_{stage}.csv'])

    fig,bg=base('B06','같은 seed끼리 비교하면 작은 증류 차이의 변동이 보인다','4월 All · 점=개별 seed 차이 / 마름모=평균 · 기준선 0보다 오른쪽이면 앞 모델이 높음','5 seed의 짝지은 차이 · 범위는 신뢰구간이 아님 · 유의성 검정 없이 작은 평균 차이를 확정적 우위로 말하지 않음')
    for j,comp in enumerate(['M2−M1','M5−M3','M5−M4']):
        ax=fig.add_axes([.16+j*.28,.25,.235,.47]);ax.axvline(0,color='#A5B4BA',lw=1.3)
        for i,stage in enumerate(STAGES):
            # Difference derived from matched per-seed performance arrays, not difference SDs.
            a,b=comp.split('−');diff=100*(np.array(row(stage,a)['macro_f1']['per_seed'])-np.array(row(stage,b)['macro_f1']['per_seed']))
            assert np.isclose(diff.mean(),pair(stage,comp)['mean_pp'])
            yy=np.full(5,5-i)+np.linspace(-.10,.10,5);ax.scatter(diff,yy,s=28,color=COLORS[a],alpha=.55);ax.scatter(diff.mean(),5-i,marker='D',s=60,color=COLORS[a],edgecolor='white',zorder=3)
        ax.set(yticks=range(6),yticklabels=list(reversed(STAGELABEL)) if j==0 else ['']*6,title=comp+' (%p)',ylim=(-.5,5.5));ax.tick_params(axis='y',length=0,labelsize=12);ax.grid(axis='x',color=LINE)
    tx(bg,8,1.4,'seed는 학습 표본·초기값·순서를 함께 바꿈 · 같은 평가 플로우를 사용한 반복',15,ha='center')
    save('B06_paired_differences','seed별 짝지은 성능 차이',fig,'M2−M1의 평균과 M5−M3/M5−M4의 작은 개선을 각 seed 수준에서 확인한다.','backup')

def export_data():
    data_csv('all_aggregate_results',['stage','model','month','group','seed_n','macro_f1_mean','macro_f1_sd','accuracy_mean','accuracy_sd'],[[r['stage'],r['model'],r['month'],r['group'],'/'.join(map(str,r['n'])),r['macro_f1']['mean'],r['macro_f1']['sd'],r['accuracy']['mean'],r['accuracy']['sd']] for r in S['rows']])
    data_csv('all_class_results',['stage','month','service','support','model','precision','recall','f1'],[[r['stage'],r['month'],r['service'],r['support'],m]+[v[k] for k in ['per_class_precision','per_class_recall','per_class_f1']] for r in S['class_rows'] for m,v in r['models'].items()])
    data_csv('all_cpu_results',['stage','model','parameters','median_ms','p95_ms','batch128_flows_s','inference_MiB','warm_RSS_MiB'],[[r['stage'],r['model'],r['parameters']]+[r[k]['mean'] for k in ['batch1_median_ms','batch1_p95_ms','batch128_flows_s','inference_MiB','warm_RSS_MiB']] for r in S['cpu_rows']])
    data_csv('all_neural_learning_curves',['stage','model','seed','epoch','train_loss','validation_f1','validation_ce'],[[r['stage'],r['model'],r['seed'],h['epoch'],h['train_loss'],h['validation']['macro_f1'],h['validation']['gt_cross_entropy']] for r in D['main_training'] if r['model']!='M0' for h in r.get('history_compact',[])])
    data_csv('all_per_seed_scores',['stage','model','month','group','seed','support','macro_f1','accuracy'],[[r['stage'],r['model'],r['month'],r['group'],201+i,r['n'][i],r['macro_f1']['per_seed'][i],r['accuracy']['per_seed'][i]] for r in S['rows'] for i in range(5)])
    data_csv('all_paired_differences',['stage','month','comparison','seed','difference_pp','mean_pp','sd_pp'],[[r['stage'],r['month'],r['comparison'],201+i,v,r['mean_pp'],r['sd_pp']] for r in S['paired'] for i,v in enumerate(r['per_seed_pp'])])
    data_csv('B04_lr_candidates',['model','candidate','mean_validation_macro_f1','selected'],[[m,r['candidate'],r['mean_macro_f1'],r['candidate']==D['development_selection']['selected'][m]] for m,rr in D['development_selection']['lr_comparisons'].items() for r in rr])

def package():
    from PIL import Image
    for a in ASSETS:
        with Image.open(HERE/a['png']) as im:a['png_pixels']=list(im.size)
    ASSETS.sort(key=lambda a:(a['id'].startswith('B'),a['id']))
    for a in ASSETS:
        if a['id'] in ['06_main_performance','07_label_budget','08_service_cohorts','B02_overlap']:a['data']=['all_aggregate_results.csv','all_per_seed_scores.csv']
        elif a['id']=='10_accuracy_cost':a['data']=['all_cpu_results.csv','all_aggregate_results.csv']
        elif a['id'] in ['B03_validation_curves','B03L_train_validation_loss']:a['data']=['all_neural_learning_curves.csv']
        elif a['id']=='B06_paired_differences':a['data']=['all_paired_differences.csv']
        elif a['id']=='B04_selection':a['data'].append('B04_lr_candidates.csv')
        a['data']=list(dict.fromkeys(a['data']))
    CHECKS[:]=list(dict.fromkeys(CHECKS))
    meta={'source_sha256':SOURCES,'assets':ASSETS,'checks':CHECKS,'format':{'png':'Opaque white; dimensions in each asset png_pixels. Standard assets 16:9; paper-style diagrams use native aspect ratios.','svg':'Text outlined; font-independent vector','svg_text':'Text retained; Apple SD Gothic Neo or compatible Korean font needed'},'new_training':False,'new_inference':False,'data_scope':'Reformatted verified results; confusion rates newly aggregated from saved confusion matrices.'}
    (HERE/'manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    cards=[]
    for a in ASSETS:
        links=' · '.join(f'<a href="{a[k]}">{lab}</a>' for k,lab in [('png','PNG'),('svg','벡터 SVG'),('editable_svg','텍스트 SVG')])
        if a['data']:links+='<br>'+ ' · '.join(f'<a href="data/{f}">수치 CSV {i+1}</a>' for i,f in enumerate(a['data']))
        cards.append(f'<section class="card" id="{a["id"]}"><div class="meta">{a["id"]} · {"본문" if a["group"]=="main" else "상세/부록"}</div><h2>{html.escape(a["title"])}</h2><a href="{a["png"]}"><img loading="lazy" src="{a["png"]}" alt="{html.escape(a["title"])}"></a><p>{html.escape(a["caption"])}</p><nav>{links}</nav></section>')
    page='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>중간발표 시각자료 모음</title><style>body{margin:0;background:#edf3f5;color:#193744;font-family:"Apple SD Gothic Neo","Malgun Gothic",sans-serif}header,main{max-width:1200px;margin:auto;padding:30px}header p{line-height:1.8}h1{font-size:34px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(460px,1fr));gap:24px}.card{background:white;border-radius:14px;padding:22px;border:1px solid #d7e3e8}h2{font-size:21px}.meta{color:#077c82;font-weight:bold}img{width:100%;border:1px solid #edf3f5}p{line-height:1.65}a{color:#077c82}nav{font-weight:bold}@media(max-width:600px){main{display:block;padding:12px}.card{margin-bottom:20px}header{padding:20px}}</style><header><h1>중간발표 시각자료 모음</h1><p>핵심 10종과 결과표·구조 상세·질의응답용 보조 자료를 함께 제공합니다. PNG는 바로 삽입, SVG는 확대·벡터 편집에 사용하세요. 04P·04Q·04R은 레이어와 분기 경로를 표시한 새 논문식 모델 구조도입니다. 원본 수치는 data/ CSV에 있습니다. 실험 조건과 주석은 그림과 함께 유지하세요.</p><p><a href="README.md">사용 안내와 발표 순서</a> · <a href="manifest.json">그림별 설명·출처</a></p></header><main>'''+''.join(cards)+'</main></html>'
    (HERE/'index.html').write_text(page)
    lines=['# 중간발표 시각자료','',f'총 {len(ASSETS)}종. 과학적 도식·통계 그래프이며 새 학습이나 추론을 수행하지 않았다.','',
    '## 사용 방법','','- `png/`: 고해상도 이미지. 일반 자료는 3200×1800(16:9), 논문식 구조도 04P·04Q·04R은 그림에 맞춘 비율이다. PPT에 원본 비율을 유지해 삽입한다.','- `svg/`: 글자를 윤곽선으로 변환한 벡터. 폰트가 없어도 모양을 유지한다.','- `svg_text/`: 텍스트를 유지한 편집용 SVG. Apple SD Gothic Neo 또는 호환 한글 폰트가 필요하다.','- `data/`: 그래프·표의 원본 수치 CSV. 표의 이미지를 편집하려면 이 수치로 PPT 표를 만들 수 있다.','- `index.html`: 전체 미리보기와 다운로드 링크.','- `build_assets.py`: 수치/레이아웃 재생성 원본. 프로젝트 원본 및 matplotlib이 있는 환경에서 실행한다.','',
    '## 권장 본문 순서','','01 입력 → 02 데이터 → 03 비교 설계 → 04 구조 → 05 증류 → 06 대표 결과 → 07 라벨 수 → 08 서비스 구성 → 09 혼동 → 10 비용.','모델 구조는 04P(교사 전체) → 04Q(잔차 블록 내부) → 04R(학생 전체)을 사용한다. 기존 04는 간단한 개요용이다.\n06T는 대표 결과 수치표, 03B는 수행 범위를 설명하는 보조 자료다. 04D·09D·B로 시작하는 자료는 질의응답에 사용한다.','',
    '## 해석 주의','','- M2/M5 색상과 모델 역할을 그림 사이에서 유지했다.','- 실제 예시가 아닌 패킷 숫자는 01에 설명용 예시로 표시했다.','- %는 점수, %p는 점수 차이. 오차막대는 5개 seed의 표본 SD로 신뢰구간이 아니다.','- Google·Meta 혼동 그림의 부분집합은 나머지 예측을 기타 열에 합산한다. 행 합계는 100%다.','- Meta 전용 모델을 학습한 것은 아니다. 비Google13 안의 6개 Meta 서비스를 표시했다.','- CPU 추론 속도는 모델 내부 벤치마크이며 패킷 대기·수집·전체 전처리를 포함한 실시간 성능이 아니다.','- 4/5월은 프로젝트에서 이미 관찰한 시간차 평가이며 완전히 새로운 외부 평가라고 소개하지 않는다.','- 전체 모델 원장과 원본 실험 기록은 기존 연구 보고서에 보존한다.','',
    '## 자료 목록','']
    lines[lines.index('## 자료 목록'):lines.index('## 자료 목록')]=['## 수치 CSV 읽기','','- F1·Accuracy·Precision·Recall은 기본적으로 0–1 값이다. `_pct` 열과 혼동행렬 셀은 0–100%다.','- `_pp`는 퍼센트포인트 차이, SD는 seed 간 표본 표준편차다.','- 표본이 없는 집합의 빈 지표는 0점이 아니라 계산할 수 없는 값이다.','- `all_per_seed_scores.csv`와 `all_paired_differences.csv`에는 개별 seed 수치도 있다.','']
    for a in ASSETS:lines.extend([f"### {a['id']} · {a['title']}",a['caption'],''])
    (HERE/'README.md').write_text('\n'.join(lines))
    from PIL import Image, ImageOps, ImageDraw, ImageFont
    font=ImageFont.truetype(font_path,22)
    for batch,start in enumerate(range(0,len(ASSETS),12),1):
        part=ASSETS[start:start+12];sheet=Image.new('RGB',(1620,4*345),(237,243,245));draw=ImageDraw.Draw(sheet)
        for i,a in enumerate(part):
            x=(i%3)*540;y=(i//3)*345
            im=Image.open(HERE/a['png']);im.thumbnail((520,293));sheet.paste(im,(x+10,y+5));draw.text((x+12,y+300),a['id']+' · '+a['title'][:20],font=font,fill=INK)
        sheet.save(HERE/f'preview_{batch}.png')
    out=HERE.parent/'midterm_presentation_assets.zip'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(HERE.rglob('*')):
            if p.is_file() and 'review' not in p.relative_to(HERE).parts and '__pycache__' not in p.parts:z.write(p,Path(HERE.name)/p.relative_to(HERE))
    print(json.dumps({'assets':len(ASSETS),'folder':str(HERE),'zip':str(out),'zip_bytes':out.stat().st_size},ensure_ascii=False))

if __name__=='__main__':
    diagrams();results();confusion_figures();supplements();export_data()
    from build_architecture_figures import add_architecture_assets
    add_architecture_assets(sys.modules[__name__]);package()


