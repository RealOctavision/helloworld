"""Layer-level scientific diagrams of the implemented teacher and student."""
from pathlib import Path
import json, hashlib, sys, os
sys.path.insert(0, '/private/tmp/midterm-report-plot')
os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/midterm-report-mpl-cache')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Circle

EDGE='#3D454C'; TEXT='#252B30'; GROUP='#EDEEEF'; WHITE='white'; MUTED='#626B73'

def canvas(w,h):
    fig=plt.figure(figsize=(w,h));ax=fig.add_axes([0,0,1,1])
    ax.set(xlim=(0,w),ylim=(0,h));ax.axis('off')
    return fig,ax

def text(ax,x,y,label,size=13,weight='normal',color=TEXT,rotation=0,ha='center'):
    return ax.text(x,y,label,fontsize=size,fontweight=weight,color=color,
                   ha=ha,va='center',rotation=rotation,linespacing=1.3)

def rect(ax,x,y,w,h,label='',size=13,fill=WHITE,rotation=0):
    ax.add_patch(Rectangle((x,y),w,h,facecolor=fill,edgecolor=EDGE,lw=1.25))
    if label:text(ax,x+w/2,y+h/2,label,size,rotation=rotation)

def panel(ax,x,y,w,h,label):
    rect(ax,x,y,w,h,fill=GROUP);text(ax,x+w/2,y+h-.34,label,16,'bold',MUTED)

def arrow(ax,x1,y1,x2,y2,dashed=False):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',
        mutation_scale=13,lw=1.15,color=EDGE,linestyle='--' if dashed else '-'))

def line(ax,points,dashed=False):
    ax.plot([p[0] for p in points],[p[1] for p in points],color=EDGE,lw=1.15,ls='--' if dashed else '-',solid_capstyle='butt')

def stack(ax,x,y,w,sections,fill=GROUP):
    """y is top; sections are (label, height, fontsize)."""
    for label,h,fs in sections:
        y-=h;rect(ax,x,y,w,h,label,fs,fill)
    return y

def save(B,code,title,fig,caption):
    fig.savefig(B.HERE/'png'/f'{code}.png',dpi=240)
    with plt.rc_context({'svg.fonttype':'path'}):fig.savefig(B.HERE/'svg'/f'{code}.svg')
    with plt.rc_context({'svg.fonttype':'none'}):fig.savefig(B.HERE/'svg_text'/f'{code}.svg')
    B.ASSETS.append({'id':code,'title':title,'group':'main','caption':caption,'data':[],
       'png':f'png/{code}.png','svg':f'svg/{code}.svg','editable_svg':f'svg_text/{code}.svg'})
    plt.close(fig)

def add_architecture_assets(B):
    for rel in ['experiments/2026-10-30_midterm_restart/models.py',
       'research/2026-09-22_plan_support/.venv/lib/python3.12/site-packages/cesnet_models/architectures/multimodal_cesnet_enhanced.py']:
        B.SOURCES[rel]=hashlib.sha256((B.ROOT/rel).read_bytes()).hexdigest()

    # Tensor labels omit the batch dimension and use channels × packets.
    fig,ax=canvas(18.8,6.1)
    panel(ax,.35,1.05,6.2,4.7,'Packet embedding stem')
    rect(ax,.65,1.65,.55,3.35,'PPI input · 3 × 30',13,rotation=90)
    branches=[(4.55,'IPT embedding\n200 bins × 10','10 × 30'),
              (3.25,'Direction indicators\n[DIR > 0, DIR < 0]','2 × 30'),
              (1.95,'SIZE embedding\n1501 entries × 20','20 × 30')]
    for y,label,shape in branches:
        arrow(ax,1.2,y,1.7,y);rect(ax,1.7,y-.45,2.55,.9,label,13)
        arrow(ax,4.25,y,5.30,y);text(ax,4.77,y+.20,shape,11)
    rect(ax,5.3,1.5,.63,3.5,'Concatenate',13,rotation=90)
    arrow(ax,5.93,3.25,7.05,3.25);text(ax,6.50,3.50,'32 × 30',12)

    panel(ax,7.05,1.05,5.35,4.7,'Residual convolutional blocks')
    panel(ax,14.85,1.05,3.55,4.7,'Target classifier')
    blocks=[(7.38,32,192,48,7,'0'),(8.60,192,256,64,7,'0.1'),
            (9.82,256,384,96,5,'0.2'),(11.04,384,448,112,3,'0.3')]
    for i,(x,ci,co,cm,k,r) in enumerate(blocks,1):
        rect(ax,x,1.55,.88,3.35,f'Bottleneck {i}: {ci} → {co}\nmid={cm} · k={k} · r={r}',12,rotation=90)
        if i<4:arrow(ax,x+.88,3.25,x+1.22,3.25)
    arrow(ax,11.92,3.25,13.2,3.25);text(ax,12.58,3.50,'448 × 30',12)
    rect(ax,13.2,2.05,.65,2.4,'GeM pooling',14,rotation=90)
    text(ax,13.525,1.63,'learnable p',11)
    arrow(ax,13.85,3.25,15.1,3.25);text(ax,14.47,3.50,'448',12)
    rect(ax,15.1,2.65,1.65,1.2,'Linear\n448 → C',14)
    arrow(ax,16.75,3.25,17.45,3.25)
    rect(ax,17.45,2.35,.65,1.8,'Logits · C',13,rotation=90)
    text(ax,16.625,1.64,'C = number of services',12)
    text(ax,.45,.58,'M1 / M2 teacher  ·  Tensor labels: channels × packets; batch omitted  ·  Stride 1 throughout',12,ha='left')
    text(ax,.45,.22,'Our implementation: pooled 448-D features → new classifier; feature refinement and the 256-D wrapper neck are not used.',11,color=MUTED,ha='left')
    save(B,'04P_teacher_architecture','논문식 구조도 · 교사 전체',fig,
         'M1/M2의 실제 forward 경로. 채널×패킷 표기로 배치 차원을 생략했다. 임베딩 연결 순서는 IPT(10)→DIR(2)→SIZE(20)이며, 448차원 GeM 뒤에 새 Linear(448,C)를 바로 연결한다. 참고 그림의 Feature Refinement 및 공개 wrapper의 256차원 neck은 사용하지 않는다.')

    fig,ax=canvas(9.6,11.3)
    text(ax,4.8,10.88,'Residual bottleneck block',20,'bold')
    text(ax,5.75,10.32,r'$C_{in}\times 30$',14)
    arrow(ax,5.75,10.05,5.75,9.45)
    line(ax,[(5.75,9.95),(1.8,9.95),(1.8,7.18)])
    arrow(ax,1.8,7.18,1.8,6.85)
    stack(ax,4.0,9.45,3.5,[('Conv1d  ·  kernel 1\n$C_{in} \\rightarrow C_{mid}$',.85,14),('BatchNorm1d + ReLU',.52,13)])
    arrow(ax,5.75,8.08,5.75,7.68)
    stack(ax,4.0,7.68,3.5,[('Conv1d  ·  kernel k\n$C_{mid} \\rightarrow C_{mid}$',.85,14),('BatchNorm1d + ReLU',.52,13)])
    arrow(ax,5.75,6.31,5.75,5.91)
    stack(ax,4.0,5.91,3.5,[('Conv1d  ·  kernel 1\n$C_{mid} \\rightarrow C_{out}$',.85,14),('BatchNorm1d',.52,13)])
    arrow(ax,5.75,4.54,5.75,4.14)
    rect(ax,4.0,3.58,3.5,.56,'Dropout (r)',14,fill=GROUP)
    arrow(ax,5.75,3.58,5.75,3.03)
    ax.add_patch(Circle((5.75,2.80),.23,edgecolor=EDGE,facecolor=WHITE,lw=1.25))
    text(ax,5.75,2.8,'+',22)
    stack(ax,.55,6.85,2.5,[('Conv1d · kernel 1\n$C_{in} \\rightarrow C_{out}$',.85,13),('BatchNorm1d',.52,13)])
    text(ax,2.04,7.14,'Projection shortcut',11,ha='left')
    line(ax,[(1.8,5.48),(1.8,2.8),(5.20,2.8)])
    arrow(ax,5.20,2.8,5.51,2.8)
    text(ax,3.15,3.02,'skip connection',12)
    arrow(ax,5.75,2.57,5.75,2.20)
    rect(ax,4.65,1.63,2.2,.57,'ReLU',14,fill=GROUP)
    arrow(ax,5.75,1.63,5.75,1.15);text(ax,5.75,.90,r'$C_{out}\times 30$',14)
    text(ax,.55,1.40,'C_mid = C_out / 4\nstride = 1; length = 30',12,ha='left')
    text(ax,4.8,.37,'Blocks 1–4: (C_in, C_out, k, r) = (32,192,7,0), (192,256,7,0.1),\n(256,384,5,0.2), (384,448,3,0.3).  Projection is used in all four blocks.',11,color=MUTED)
    save(B,'04Q_residual_bottleneck','논문식 구조도 · 잔차 블록 내부',fig,
         '현재 교사의 네 블록은 모두 입출력 채널 수가 달라 1×1 Conv+BN projection을 사용한다. Dropout은 잔차 가지의 마지막 BN 이후, 합산 이전이다. 첫 블록 r=0은 Identity이며 모든 stride는 1이다.')

    fig,ax=canvas(20.4,6.0)
    rect(ax,.35,2.25,1.2,1.35,'PPI\n3 × 30',14)
    panel(ax,1.90,1.2,3.10,3.25,'Fixed transform')
    arrow(ax,1.55,2.925,2.1,2.925)
    rect(ax,2.1,2.15,2.7,1.55,'IPT: log-scale\nDIR: unchanged\nSIZE: ÷1500',13)
    line(ax,[(.95,3.6),(.95,5.25),(2.1,5.25)],True)
    rect(ax,2.1,4.88,2.7,.74,'Mask  m = [DIR ≠ 0]',13)
    line(ax,[(4.8,5.25),(15.65,5.25)],True)
    text(ax,3.45,1.47,'3 × 30',12)
    for i,(x,ci,co) in enumerate([(5.65,3,32),(8.45,32,64),(11.25,64,64)],1):
        rect(ax,x-.18,1.2,2.56,3.25,fill=GROUP)
        text(ax,x+.95,4.13,f'Conv block {i}',14,'bold',MUTED)
        rect(ax,x,1.82,1.08,2.18,f'Conv1d  {ci} → {co}\nk=3 · padding=1',12,rotation=90)
        arrow(ax,x+1.08,2.925,x+1.30,2.925)
        rect(ax,x+1.30,1.82,.40,2.18,'ReLU',12,rotation=90)
        arrow(ax,x+1.70,2.925,x+1.96,2.925)
        ax.add_patch(Circle((x+2.10,2.925),.14,edgecolor=EDGE,facecolor=WHITE,lw=1.2))
        text(ax,x+2.10,2.925,'×',16)
        arrow(ax,x+2.10,5.25,x+2.10,3.08,True)
        text(ax,x+1.10,1.47,f'{co} × 30',12)
    for start,end in [(4.8,5.65),(7.89,8.45),(10.69,11.25)]:
        arrow(ax,start,2.925,end,2.925)
    arrow(ax,13.49,2.925,14.75,2.925)
    text(ax,14.10,2.55,'64 × 30',11)
    rect(ax,14.75,2.10,1.8,1.65,'Masked\nmean pooling',13,fill=GROUP)
    arrow(ax,15.65,5.25,15.65,3.75,True)
    arrow(ax,16.55,2.925,17.25,2.925);text(ax,16.90,3.23,'64',12)
    rect(ax,17.25,2.20,1.45,1.45,'Linear\n64 → C',14,fill=GROUP)
    arrow(ax,18.70,2.925,19.20,2.925)
    rect(ax,19.20,2.05,.65,1.75,'Logits · C',13,rotation=90)
    text(ax,12.3,5.58,'Mask is computed from the input and reused after every Conv–ReLU and in pooling.',12,color=MUTED)
    text(ax,.45,.66,'M3 / M4 / M5 student  ·  Shared architecture; different training losses  ·  No BatchNorm, dropout, or residual connections',12,ha='left')
    text(ax,.45,.25,r'IPT transform: log(1 + IPT_ms) / log(1 + 65000)    |    Pool: Σₜ(mₜ · hₜ) / max(Σₜ mₜ, 1)    |    C = number of services',12,color=MUTED,ha='left')
    save(B,'04R_student_architecture','논문식 구조도 · 학생 전체',fig,
         'M3/M4/M5의 동일한 구조. 입력은 공통 clip·패딩 후이며 DIR≠0에서 만든 마스크를 각 Conv→ReLU 뒤에 곱하고 pooling 분모에도 사용한다. 실선은 특징, 점선은 마스크 경로다. [B,채널,패킷]에서 B를 생략했다.')
    B.CHECKS.append('Paper-style architecture paths matched to models.py and installed CESNET Bottleneck/forward_features; no new inference.')

if __name__=='__main__':
    import build_assets as B
    previous=json.loads((B.HERE/'manifest.json').read_text())
    new_ids={'04P_teacher_architecture','04Q_residual_bottleneck','04R_student_architecture'}
    B.ASSETS[:]=[a for a in previous['assets'] if a['id'] not in new_ids]
    B.SOURCES.update(previous['source_sha256']);B.CHECKS[:]=previous['checks']
    add_architecture_assets(B);B.package()
