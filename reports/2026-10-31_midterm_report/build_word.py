"""Readable Word edition of the reviewed HTML; no experiment execution."""
from pathlib import Path
import json, re, hashlib, statistics
from lxml import html, etree
from docx import Document
from docx.shared import Mm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE/'report_data.json').read_text())
S = DATA['summary']; D = DATA['data_manifest']
TREE = html.fromstring((HERE/'report.html').read_text())
ARTICLE = TREE.xpath('//article')[0]
FONT = 'Apple SD Gothic Neo'
doc = Document()
sec = doc.sections[0]
sec.page_width = Mm(210); sec.page_height = Mm(297)
sec.top_margin = Mm(19); sec.bottom_margin = Mm(18)
sec.left_margin = Mm(20); sec.right_margin = Mm(20)
sec.header_distance = Mm(8); sec.footer_distance = Mm(8)
WIDTH = 170

def set_font(style, size, bold=False):
    style.font.name = FONT; style.font.size = Pt(size)
    style.font.bold = bold; style.font.italic = False; style.font.color.rgb = RGBColor(0,0,0)
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None: rf=OxmlElement('w:rFonts'); rpr.insert(0,rf)
    for k in ['ascii','hAnsi','eastAsia','cs']: rf.set(qn('w:'+k),FONT)
    for k in ['asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme']: rf.attrib.pop(qn('w:'+k),None)

for n in ['Normal','Body Text','List Bullet','List Number']:
    set_font(doc.styles[n],10.5)
    pf=doc.styles[n].paragraph_format
    pf.line_spacing=1.24; pf.space_after=Pt(6)
    pf.widow_control=True
set_font(doc.styles['Title'],25,True)
doc.styles['Title'].paragraph_format.space_after=Pt(12)
set_font(doc.styles['Subtitle'],12)
doc.styles['Subtitle'].paragraph_format.space_after=Pt(9)
for n,size in [('Heading 1',17),('Heading 2',12.5),('Heading 3',11)]:
    set_font(doc.styles[n],size,True)
    pf=doc.styles[n].paragraph_format
    pf.space_before=Pt(12); pf.space_after=Pt(7)
    pf.keep_with_next=True
doc.styles['Heading 1'].paragraph_format.page_break_before=False
for border in list(doc.styles.element.xpath('.//w:pBdr')):
    border.getparent().remove(border)
set_font(doc.styles['Caption'],9)
doc.styles['Caption'].paragraph_format.space_after=Pt(8)
doc.styles['Caption'].paragraph_format.line_spacing=1.12
set_font(doc.styles['Header'],8.5)
set_font(doc.styles['Footer'],8.5)
head=sec.header.paragraphs[0]
head.text='암호화 QUIC 트래픽 분류   |   중간발표 실험 보고서'
foot=sec.footer.paragraphs[0];foot.alignment=WD_ALIGN_PARAGRAPH.CENTER
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE')
foot._p.append(fld)
doc.core_properties.title='암호화 QUIC 트래픽 분류 실험 보고서'
doc.core_properties.subject='데이터 처리와 M0 M5 비교 실험의 방법 결과 해석'
doc.core_properties.author='캡스톤 연구팀'
doc.core_properties.keywords='QUIC, PPI, 전이학습, 지식 증류, CESNET'

def txt(el):
    return re.sub(r'\s+',' ',el.text_content()).strip()

def heading_title(s):
    s=re.sub(r'^\d+(?:\.\d+)*\.?(?:\s+)', '',s)
    s=s.replace('—',' ').replace('·',' ').replace('–',' ').replace('→',' ')
    return re.sub(r'[^\w\s가-힣αβ]+',' ',s).strip()

bookmark_id=0
def bookmark(p,name):
    global bookmark_id
    bookmark_id+=1
    a=OxmlElement('w:bookmarkStart');a.set(qn('w:id'),str(bookmark_id));a.set(qn('w:name'),name)
    b=OxmlElement('w:bookmarkEnd');b.set(qn('w:id'),str(bookmark_id))
    p._p.insert(0,a);p._p.append(b)

def add_link(p,label,url=None,anchor=None):
    h=OxmlElement('w:hyperlink')
    if anchor: h.set(qn('w:anchor'),anchor)
    else: h.set(qn('r:id'),p.part.relate_to(url,RT.HYPERLINK,is_external=True))
    r=OxmlElement('w:r');pr=OxmlElement('w:rPr')
    col=OxmlElement('w:color');col.set(qn('w:val'),'1A526B');pr.append(col)
    rf=OxmlElement('w:rFonts')
    for k in ['ascii','hAnsi','eastAsia']:rf.set(qn('w:'+k),FONT)
    pr.append(rf);r.append(pr)
    t=OxmlElement('w:t');t.text=label;r.append(t);h.append(r);p._p.append(h)

def inline(p,el,bold=False,italic=False,sub=False,super_=False):
    def run(s):
        if not s:return
        r=p.add_run(s);r.bold=bold;r.italic=italic
        r.font.subscript=sub;r.font.superscript=super_
    run(el.text)
    for c in el:
        tag=c.tag
        if not isinstance(tag,str):continue
        if tag=='br':p.add_run().add_break()
        elif tag=='a':
            u=c.get('href','')
            if u.startswith('#'):add_link(p,txt(c),url='report.html'+u)
            else:add_link(p,txt(c),url=u)
        elif tag in ('strong','b'):inline(p,c,True,italic,sub,super_)
        elif tag in ('em','i'):inline(p,c,bold,True,sub,super_)
        elif tag=='sub':inline(p,c,bold,italic,True,False)
        elif tag=='sup':inline(p,c,bold,italic,False,True)
        elif tag=='button':pass
        else:inline(p,c,bold,italic,sub,super_)
        run(c.tail)

def para(s='',style=None):
    return doc.add_paragraph(s,style)

table_count=0
def table(headers,rows,widths=None,label=None,compact=False):
    global table_count
    table_count+=1
    if label:
        p=para(label,'Caption');p.paragraph_format.keep_with_next=True
    n=len(headers)
    if widths is None:
        if n==2: widths=[51,119]
        elif n==3: widths=[36,67,67]
        elif n==4: widths=[27,49,49,45]
        elif n==5: widths=[30,35,35,35,35]
        else: widths=[170/n]*n
    widths=[w*WIDTH/sum(widths) for w in widths]
    t=doc.add_table(rows=1,cols=n);t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
    for c,w in zip(t.columns,widths):c.width=Mm(w)
    pr=t._tbl.tblPr
    borders=OxmlElement('w:tblBorders')
    for name in ['top','left','bottom','right','insideH','insideV']:
        b=OxmlElement('w:'+name)
        for k,v in [('val','single'),('sz','4'),('color','D9D9D9')]:b.set(qn('w:'+k),v)
        borders.append(b)
    pr.append(borders)
    margin=OxmlElement('w:tblCellMar')
    for k,v in [('top',40 if compact else 70),('bottom',40 if compact else 70),('left',75),('right',75)]:
        a=OxmlElement('w:'+k);a.set(qn('w:w'),str(v));a.set(qn('w:type'),'dxa');margin.append(a)
    pr.append(margin)
    hr=t.rows[0]._tr.get_or_add_trPr();repeater=OxmlElement('w:tblHeader');hr.append(repeater)
    records=[headers]+list(rows)
    for ri,values in enumerate(records):
        cells=t.rows[0].cells if ri==0 else t.add_row().cells
        rowpr=cells[0]._tc.getparent().get_or_add_trPr()
        rowpr.append(OxmlElement('w:cantSplit'))
        for ci,(cell,value) in enumerate(zip(cells,values)):
            cell.width=Mm(widths[ci]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'DCE8ED' if ri==0 else ('F5F8FA' if ri%2==0 else 'FFFFFF'));cell._tc.get_or_add_tcPr().append(sh)
            p=cell.paragraphs[0];p.paragraph_format.space_after=Pt(1);p.paragraph_format.space_before=Pt(1)
            p.paragraph_format.line_spacing=1.12;p.paragraph_format.keep_with_next=(ri==0)
            s=str(value)
            if ri==0 or (len(s)<26 and re.fullmatch(r'[\d\s.,/%±+−→()A-Z_–a-z=]+',s)):
                p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            if isinstance(value,etree._Element): inline(p,value)
            else:p.add_run(s)
            for r in p.runs:
                r.font.size=Pt(9.3 if n<7 else 8.5);r.bold=(ri==0);r.font.color.rgb=RGBColor(0,0,0)
    spacer=para();spacer.paragraph_format.space_after=Pt(2);spacer.paragraph_format.space_before=Pt(0)
    spacer.paragraph_format.line_spacing=Pt(2)
    return t

def html_table(el):
    rows=el.xpath('./thead/tr|./tbody/tr|./tr')
    if not rows:return
    cols=[r.xpath('./th|./td') for r in rows]
    h=[txt(c) for c in cols[0]]
    n=len(h);widths=None
    if h[0]=='용어':widths=[33,89,48]
    elif h[0]=='연구 질문':widths=[63,32,75]
    elif h[0]=='모델' and n==4:widths=[14,61,48,47]
    elif h[0]=='4월 조건':widths=[38,33,33,33,33]
    elif h[0]=='서비스당 정답' or h[0]=='4월 구성':widths=[26]+[24]*6
    elif h[0]=='모델' and n==7:widths=[13,24,27,27,28,24,27]
    elif h[0]=='다음 질문':widths=[47,53,48,22]
    table(h,cols[1:],widths)

figure_count=0;deferred=[]
def consume(el):
    global figure_count
    if not isinstance(el.tag,str):return
    tag=el.tag;cls=el.get('class','')
    if tag=='h1':return
    if tag in ['h2','h3','h4']:
        level=int(tag[1])-1
        s=txt(el)
        if level==1:
            n=re.match(r'^(\d+)\.',s)
            s=(n[1]+' ' if n else '')+heading_title(s)
        else:s=heading_title(s)
        p=doc.add_heading(s,level)
        if el.get('id'):bookmark(p,el.get('id'))
    elif tag=='p':
        if txt(el).startswith('읽는 방법.'):
            return  # Already covered by the Word contents and metric definitions.
        inline(para(),el)
    elif tag=='table':html_table(el)
    elif tag=='figure':
        names=['representative','collision','label_curve','cohorts','class_heatmap','learning_curves','cost_accuracy']
        name=names[figure_count];figure_count+=1
        p=para();p.paragraph_format.keep_with_next=True;p.paragraph_format.space_after=Pt(2)
        r=p.add_run();r.add_picture(str(HERE/'figures'/f'{name}.png'),width=Mm(168))
        for drawing in r._r.xpath('.//wp:docPr'):drawing.set('descr',txt(el.xpath('./figcaption')[0]))
        para(txt(el.xpath('./figcaption')[0]),'Caption')
    elif tag=='blockquote':
        p=para();inline(p,el);p.paragraph_format.left_indent=Mm(4)
    elif tag in ['ol','ul']:
        for c in el.xpath('./li'):
            p=para(style='List Number' if tag=='ol' else 'List Bullet');inline(p,c)
    elif tag=='pre':
        p=para(el.text_content().rstrip());p.paragraph_format.line_spacing=1.02
        p.paragraph_format.keep_together=True;p.paragraph_format.left_indent=Mm(4)
        for r in p.runs:r.font.size=Pt(8.8);r.font.name='Menlo';r._r.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),FONT)
    elif tag=='details':
        # HTML keeps every raw detail. Word moves implementation details to appendix D.
        if '개발 후보 평균' in txt(el.xpath('./summary')[0]):
            p=para('개발 후보 전체 점수와 개별 실행 기록은 HTML 부록 A에서 확인할 수 있다.');p.paragraph_format.space_after=Pt(7)
        else:deferred.append(el)
    elif tag=='div':
        if cls in ['eyebrow','cover-meta']:return
        if cls=='stat-grid':
            para('비교 모델 6개  ·  본실험 학습 180회  ·  월간 평가 360건  ·  CPU 측정 180개')
        elif cls=='flow-strip':
            p=para('원본과 서비스 선택 → 유효성 검사 → 입력 정규화 → 1월 중복 정리 → 균등 추출 → 고정 검증과 월간 평가')
            for r in p.runs:r.bold=True
        elif cls=='formula':
            p=para();inline(p,el);p.paragraph_format.keep_together=True
        else:
            for c in el:consume(c)

# First page is a useful overview and clickable contents, not a decorative cover.
para('암호화 QUIC 트래픽\n분류 실험 보고서','Title')
para('첫 최대 30패킷을 이용한 사전학습과 지식 증류 비교','Subtitle')
para('캡스톤 중간발표 연구 자료  |  2026년 10월 31일')
para('이 보고서는 데이터 정제, 비교 모델, 설정 선택, 성능과 실행 비용을 한 흐름으로 설명한다. 공개 사전학습 교사는 유리한 평균 성능을 보였지만, 작은 학생으로 그 성능을 유지하는 목표에는 도달하지 못했다.')
p=para('본문과 핵심 부록을 순서대로 읽고, 발표 질의응답은 부록 E를 참고한다. 실행별 전체 원장과 원본 근거는 함께 제공되는 HTML에 보존되어 있다.')
add_link(p,' 상세 HTML 열기','report.html')
para('목차','Heading 2')
mainheads=[]
for el in ARTICLE:
    if el.tag=='h2' and not txt(el).startswith('부록'):
        mainheads.append((el.get('id'),txt(el)))
for anchor,label in mainheads:
    p=para();p.paragraph_format.space_after=Pt(3)
    add_link(p,label.split(' — ')[0],anchor=anchor)
appendices=[('wa','부록 A 개발 후보와 선택 결과'),('wb','부록 B 서비스 목록과 평가 표본'),('wc','부록 C 전체 조건별 결과와 비용'),('wd','부록 D 구현과 재현 근거'),('we','부록 E 발표 질의응답'),('wf','부록 F 참고문헌')]
for anchor,label in appendices:
    p=para();p.paragraph_format.space_after=Pt(3);add_link(p,label,anchor=anchor)

started=False
doc.add_page_break()
for el in ARTICLE:
    if el.tag=='h2':
        if txt(el).startswith('부록'):break
        started=True
    if started:consume(el)

def ah(text,anchor):
    p=doc.add_heading(text,1);p.paragraph_format.page_break_before=True;bookmark(p,anchor)
def sub(text):return doc.add_heading(text,2)
def mean_sd(v,scale=100):return f"{v['mean']*scale:.3f} ± {v['sd']*scale:.3f}"
def num(v):return f'{v:,}'
CN={'google_included20':'혼합20','non_google13':'비Google13','google_only20':'Google 계열20'}
SN={'mixed_n50':'혼합20 50개','mixed_n100':'혼합20 100개','mixed_n200':'혼합20 200개','mixed_n1000':'혼합20 1000개','nongoogle_n200':'비Google13 200개','googleonly_n200':'Google 계열20 200개'}
MODELS=['M0','M1','M2','M3','M4','M5']

ah('부록 A 개발 후보와 선택 결과','wa')
para('모든 값은 2월 검증 결과다. 학습률과 leaves는 개발 seed 2개 평균, KD는 두 교사와 두 seed에서 만든 학생 4개 평균으로 선택했다. 개별 실행 60개의 원본은 HTML 부록 A에 보존했다.')
selection=DATA['development_selection']
table(['모델','후보','평균 검증 F1 %','평균 정답 CE'],[
    [m,r['candidate'],f"{r['mean_macro_f1']*100:.3f}",f"{r['mean_gt_ce']:.3f}"]
    for m,rs in selection['lr_comparisons'].items() for r in rs],[18,38,57,57],compact=True)
sub('공통 지식 증류 설정')
table(['α','T','학생 4개 평균 검증 F1 %','평균 정답 CE'],[
    [r['alpha'],r['temperature'],f"{r['mean_macro_f1']*100:.3f}",f"{r['mean_gt_ce']:.3f}"] for r in selection['kd_grid']],[20,20,75,55],compact=True)
para('최종 공통 선택은 α 0.5와 T 1이다. 다른 예산과 서비스 구성에서는 이 값을 재탐색하지 않았다. 후보 간 차이가 작은 만큼, 해당 설정이 모든 조건의 보편적 최적값이라는 결론은 내리지 않는다.')

ah('부록 B 서비스 목록과 평가 표본','wb')
para('아래 표는 실제 출력 인덱스 순서다. 1월은 충돌과 동일 라벨 중복을 정리한 고유 후보 수이며, 2월은 모델 선택에 사용한 고정 검증 수다. 4월과 5월은 All 평가의 기록 수다.')
for cohort,c in D['cohorts'].items():
    sub(CN[cohort])
    table(['인덱스','서비스','APP 코드','1월 후보','2월 검증','4월 평가','5월 평가'],[
        [i,n,c['codes'][i],num(c['january_curation']['retained_per_class'][n]),num(c['validation_support'][i]),num(c['month_support']['202504'][i]),num(c['month_support']['202505'][i])]
        for i,n in enumerate(c['classes'])],[13,47,16,24,22,24,24])
sub('짧은 플로우와 공통 미노출 평가의 크기')
table(['구성','월','전체','30패킷 미만','공통 미노출','검증 PPI 겹침'],[
    [CN[c],mo[-2:]+'월',num(v['evaluation_'+mo]['rows']),num(v['evaluation_'+mo]['groups']['short_flow']),num(v['evaluation_'+mo]['groups']['common_unseen']),num(v['evaluation_'+mo]['groups']['validation_overlap'])]
    for c,v in D['cohorts'].items() for mo in ['202504','202505']],[34,13,30,31,32,30])
para('길이별 표본 수는 확보했지만 short/long 성능은 아직 집계하지 않았다. 검증과 학습 입력의 상세 겹침 수, 전체 12개월의 1–30패킷 충돌 진단은 HTML 부록 B에서 제공한다.')

ah('부록 C 전체 조건별 결과와 비용','wc')
para('주평가 All의 5개 seed 평균과 표본 SD다. 같은 평가 자료를 다섯 모델에 사용했다. CE는 정답 cross-entropy이며 낮을수록 좋다. 이 표에는 개발 선택 점수를 섞지 않았다.')
for stage in SN:
    sub(SN[stage])
    rr=[r for r in S['rows'] if r['stage']==stage and r['group']=='all']
    rr.sort(key=lambda r:(r['month'],r['model']))
    table(['월','모델','Macro F1 %','Accuracy %','정답 CE'],[
        [r['month'][-2:]+'월',r['model'],mean_sd(r['macro_f1']),mean_sd(r['accuracy']),mean_sd(r['gt_cross_entropy'],1)] for r in rr],[15,15,48,48,44])
sub('짝지은 주요 차이의 전체 월별 요약')
para('평균 차이의 단위는 %p다. 괄호는 차이가 양수인 seed 수이며 유의성 검정 결과가 아니다.')
rows=[]
for stage in SN:
    for mo in ['202504','202505']:
        vals=[]
        for comp in ['M2−M1','M5−M3','M5−M4']:
            r=next(r for r in S['paired'] if (r['stage'],r['month'],r['comparison'])==(stage,mo,comp))
            vals.append(f"{r['mean_pp']:+.3f} ± {r['sd_pp']:.3f} ({r['positive_seeds']}/5)")
        rows.append([SN[stage],mo[-2:]+'월']+vals)
table(['조건','월','M2 − M1','M5 − M3','M5 − M4'],rows,[37,13,40,40,40])
sub('모든 조건의 CPU 비용 요약')
para('CPU 1 thread·FP32 측정이다. 아래 값은 seed별 측정 지표의 평균이며 batch 1 median과 p95를 전체 관측의 통합 median/p95로 해석하지 않는다. 학습 비용은 포함하지 않는다.')
table(['조건','모델','median ms','p95 ms','128배치 flows/s','파일 MiB','RSS MiB'],[
    [SN[r['stage']],r['model']]+[f"{r[k]['mean']:.4f}" if 'ms' in k else f"{r[k]['mean']:.2f}" for k in ['batch1_median_ms','batch1_p95_ms','batch128_flows_s','inference_MiB','warm_RSS_MiB']]
    for r in sorted(S['cpu_rows'],key=lambda r:(list(SN).index(r['stage']),r['model']))],[34,12,25,25,30,22,22])
para('실행별 180개 학습·360개 월간 평가·180개 CPU 측정, 전체 서비스 P/R/F, 각 seed의 짝차이와 혼동 쌍은 HTML 부록 C에 보존했다. Word에서는 비교를 읽는 데 필요한 집계를 제공하며, 반복 원장을 중복 인쇄하지 않는다.')

ah('부록 D 구현과 재현 근거','wd')
for el in deferred:
    sub(heading_title(txt(el.xpath('./summary')[0])))
    for child in el:
        if child.tag!='summary':consume(child)
sub('사전학습 활용과 구조 변경의 경계')
para('공개 30pktTCNET 가중치의 backbone을 사용했다. 최종 256차원 wrapper를 그대로 분류기에 붙인 경로가 아니라 pooling 직후 448차원에 새 head를 연결한 경로다. 교사 파라미터는 686,613 + 449C, 학생은 18,880 + 65C다. C는 목표 서비스 수다.')
para('M1은 공개 학습 checkpoint 없이 생성하되 공식 생성자의 데이터 비의존 PLE 초기화는 유지한다. M2는 BN running 통계를 고정하고 affine 계수는 학습한다. 보조 크기 히스토그램 카운터의 CPU 호환성 조정은 forward 입력이나 교사의 표현을 바꾸기 위한 변경이 아니다.')
sub('실행 환경')
table(['항목','신경망 학습','CPU 추론'],[
    ['장치','NVIDIA A100 SXM4 40GB','Apple M5'],['운영 환경','Colab CUDA 13.0','macOS 27.0.1 arm64'],['Python','3.13.16','3.12.14'],['PyTorch','2.11.0+cu130','2.14.0'],['NumPy','2.1.3','2.5.3'],['cesnet models','0.4.1','0.4.1'],['LightGBM','4.6.0','4.6.0'],['정밀도','FP32 TF32 off','FP32 CPU 1 thread']], [34,68,68])
sub('보존한 자료와 검증 범위')
para('원본 HDF5·PPI 캐시·분할 manifest·동결 설정·실행 코드·초기 state·교사 대응·best/last checkpoint·학습곡선·월별 예측·CPU 측정과 환경을 보존했다. ZIP 전체 SHA256·CRC·안전 경로·내부 파일 해시, 입력 ID와 라벨, 50 epoch 완료 및 checkpoint 대응을 확인한 결과만 집계했다.')
para('월별 예측에는 원본 ID·정답·예측 라벨·정답 log확률·최대확률을 저장했다. 전체 클래스 확률벡터는 모두 보존하지 않았지만 고정 입력과 checkpoint에서 재계산할 수 있다. 소수 표본의 다른 방식 대조는 독립 연구자의 전수 검증과 다르다. 플랫폼이 다른 모든 연산의 bitwise 동일성도 보장하지 않는다.')
para('세션 소실로 회수하지 못한 30회 학습과 3개의 2 epoch 속도 측정은 성과 집계에서 제외했다. 현재 본실험 180회는 회수·검증된 고유 실행이다. 결과를 로컬에 보존한 뒤 2026년 10월 31일 03시 07분 35초 KST에 A100 해제를 기록했다.')
sub('자료를 찾는 방법')
table(['찾을 내용','위치'],[
    ['보고서 전체와 상세 원장','같은 폴더의 report.html 부록 A–F'],['전체 수치와 곡선','report.html 부록 C의 JSON 저장 버튼 또는 report_data.json'],['데이터 계약과 클래스 구성','experiments/2026-10-30_midterm_restart/prepared/manifest.json'],['고정 실험 설정','같은 실험 폴더의 main_frozen.json 및 continuation_frozen.json'],['구조와 손실 구현','같은 실험 폴더의 models.py 및 training.py'],['검증된 통합 결과','같은 실험 폴더의 continuation_recovered/continuation_summary.json'],['실행별 원본과 해시','report.html 부록 D의 원본 등록부와 근거 경로']], [49,121])
para('HTML의 표·그림·보고용 JSON은 파일 안에 포함된다. 원본 checkpoint와 개별 지표 파일 링크는 프로젝트 폴더가 함께 있어야 열린다. 보고서 복사본과 원본 연구 기록은 역할이 다르다.')

ah('부록 E 발표 질의응답','we')
for i,(q,a) in enumerate(json.loads((HERE/'qa.json').read_text()),1):
    sub(f'{i} '+q);para(a)

ah('부록 F 참고문헌','wf')
refs=[
 ('CESNET QUICEXT 25 데이터셋','https://zenodo.org/records/17249078','공개 QUIC 플로우와 패킷 정보의 출처다. 본실험은 로컬 XS 자료의 선택 서비스와 월을 사용한다.'),
 ('Waiting for QUIC','https://doi.org/10.1145/3768988','공식 데이터셋 페이지가 안내하는 인용 문헌이다.'),
 ('Universal Embedding Function for Traffic Classification via QUIC Domain Recognition Pretraining A Transfer Learning Success','https://arxiv.org/abs/2502.12930','QUIC 도메인 인식으로 사전학습한 표현의 전이 접근을 사용했다. 대규모 사전학습을 새로 실행한 것은 아니다.'),
 ('CESNET Models 공식 구현','https://github.com/CESNET/cesnet-models','교사 구조와 공개 가중치의 출처다. 실제 실행 버전은 0.4.1이며 학생 구조와 비교 설정은 본문에 명시했다.'),
 ('tc transfer 공식 구현','https://github.com/CESNET/tc-transfer','전이학습 구현의 참고 자료다. 원 논문의 전체 실험 프로토콜을 그대로 재현한 것은 아니다.'),
 ('Distilling the Knowledge in a Neural Network','https://arxiv.org/abs/1503.02531','Hinton Vinyals Dean 2015. 교사의 확률 분포를 학생에게 전달하는 지식 증류의 기반이다.'),
 ('LightGBM A Highly Efficient Gradient Boosting Decision Tree','https://papers.nips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html','Ke 등 2017. M0의 트리 학습 방법이며 16개 입력 통계는 이번 실험 코드에서 정의했다.')]
for i,(name,url,scope) in enumerate(refs,1):
    p=para();p.add_run(f'[{i}] {name}').bold=True
    p.paragraph_format.keep_with_next=True
    p=para(scope+' ');add_link(p,'원문',url)

out=HERE/'midterm_report.docx';doc.save(out)
report={'output':out.name,'paragraphs':len(doc.paragraphs),'tables':len(doc.tables),'figures':figure_count,'qa':len(json.loads((HERE/'qa.json').read_text())),'source_html_sha256':hashlib.sha256((HERE/'report.html').read_bytes()).hexdigest(),'word_scope':'All reviewed main chapters; service lists; all condition/month aggregate results and costs; implementation/environment; Q&A; sources. Per-fit raw ledgers remain in linked HTML.'}
(HERE/'review'/'word_build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
