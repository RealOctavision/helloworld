"""Build main-stage tables only from verified archives and recorded CPU benchmarks."""
from pathlib import Path
import json,statistics as st
H=Path(__file__).resolve().parent;R=H.parents[1];E=R/'experiments/2026-10-30_midterm_restart'
def link(p):return '../../'+str(p.relative_to(R))
def table(head,rows):return '\n|'+'|'.join(head)+'|\n|'+'|'.join(['---']*len(head))+'|\n'+''.join('|'+'|'.join(map(str,row))+'|\n'for row in rows)+'\n'
def ms(values,scale=1):
 v=[float(x)*scale for x in values];return f'{st.mean(v):.3f} ± {st.stdev(v):.3f}' if len(v)>1 else f'{v[0]:.3f}'
def run():
 reg=json.loads((E/'main_recovered/training_registry.json').read_text());train=json.loads((R/reg['verification']).read_text())
 f=json.loads((E/'main_frozen.json').read_text());models=['M0','M1','M2','M3','M4','M5'];seeds=f['seeds']
 text='## 대표 본실험 결과 — Google 포함20·200개·5개 seed\n\n'
 text+='개발 탐색과 별도로 seed201~205에서 M0~M5 **30fit**을 완료하고 로컬 검증했다. 신경망25fit은 각50epoch·1,600update, 트리5fit은 사전 지정한 조기종료 규칙을 사용했다. 개발 결과를 본실험의 반복에 재사용하지 않았다.\n\n'
 text+=f"[학습 원본 ZIP]({link(R/train['archive'])}) · [학습 검증 원장]({link(R/reg['verification'])}). 내부{train['verified_files']}파일. SHA256 `{train['archive_sha256']}`.\n\n"
 text+='고정 설정: M1 LR0.001 / M2 LR0.0001 / 학생 LR0.003 / LightGBM leaves31 / 공통KD α0.5·T1 /50epoch. 모든 checkpoint는2월 검증으로 선택하고 목록을 동결한 후4·5월에 평가했다. 원래 config와 데이터는 보존하고 별도 main_frozen.json을 실행기에 적용했다.\n\n'
 rows=[]
 for m in models:
  rr=[x for x in train['records']if x['model']==m]
  rows.append([m,ms([x['validation']['macro_f1'] for x in rr],100),', '.join(str(x['selected_step'])for x in rr),f"{sum(x['resources']['full_fit_seconds']for x in rr):.1f}"])
 text+='### 학습 완료와2월 checkpoint 선택\n\n다음 점수는 본seed의 **2월 검증값**이며4월 성능과 구별한다. 시간은 모델 초기화·교사 예측·학습·검증·checkpoint 저장을 포함하고 ZIP 압축·전송을 제외한다.\n'
 text+=table(['모델','2월 Macro-F1 평균±표본SD(%)','seed201~205 best epoch/round','5fit 시간 합(초)'],rows)
 evreg=E/'main_recovered/evaluation_registry.json';summary=dict(training=reg['verification'],completed_fits=30,monthly_evaluation_complete=False,cpu_benchmark_complete=False)
 if evreg.exists():
  er=json.loads(evreg.read_text());ev=json.loads((R/er['verification']).read_text());records=ev['records'];summary.update(evaluation=er['verification'],monthly_evaluation_complete=True)
  text+=f"### 4·5월 시간차 평가\n\n60건의 월×모델×seed 평가를 회수하여 모든 예측 ID·checkpoint 해시·부분집합 지표를 대조했다. [평가 원본 ZIP]({link(R/ev['archive'])}) · [평가 검증 원장·전체 클래스 지표]({link(R/er['verification'])}). SHA256 `{ev['archive_sha256']}`.\n\n"
  text+='주 결과는4월 All, 시간 변화 평가는5월 All이다. ±는5개 seed의 **표본 표준편차(ddof=1)**이며 신뢰구간이 아니다. 같은 월의 동일 평가자료를 반복 평가하므로5개 반복을 독립 수집 데이터셋5개로 보지 않는다. 학습 겹침은 각 seed의 실제200개 학습표본 기준이고 Common-unseen은 사전 등록된 학습·개발·검증 목록의 합집합과 겹치지 않는 부분집합이다.\n\n'
  by={(r['month'],r['model'],r['seed']):r for r in records}
  for month in f['evaluation_months']:
   rows=[]
   for group in ['all','train_overlap','train_nonoverlap','common_unseen']:
    for m in models:
     rr=[by[month,m,s]['groups'][group]for s in seeds];ns=[x['n']for x in rr];cs=[x['classes_with_support']for x in rr]
     rows.append([group,m,f'{min(ns):,}–{max(ns):,}',f'{min(cs)}–{max(cs)}',ms([x['macro_f1']for x in rr],100) if all(ns) else 'N/A',ms([x['accuracy']for x in rr],100) if all(ns) else 'N/A'])
   text+=f'#### {month} 전체·겹침·비겹침·공통 미관측\n'+table(['부분집합','모델','seed별 N 범위','정답 support>0 클래스 수','Macro-F1 평균±SD(%)','Accuracy 평균±SD(%)'],rows)
   text+='고정20클래스 Macro-F1이며 해당 부분집합에서 정답·예측 모두 없는 클래스의F1은0이다. 빈 집합은N/A다. 부분집합마다 클래스 구성·난이도가 달라 단순 점수 차이를 누수의 인과효과로 단정하지 않는다.\n\n'
   overlap_rows=[]
   for s in seeds:
    for m in models:
     g=by[month,m,s]['groups']['train_overlap']
     overlap_rows.append([s,m,g['n'],g['classes_with_support'],f"{100*g['macro_f1']:.3f}" if g['n'] else 'N/A',f"{100*g['accuracy']:.3f}" if g['n'] else 'N/A'])
   text+='<details><summary>학습 겹침 부분집합 — seed별 원점수</summary>\n\n'
   text+='4월 seed203은 겹침 표본이0개이므로5seed 평균은N/A로 표시한다. 다른 반복의 비어 있지 않은 결과는 아래에 그대로 남긴다. 두 월 모두 겹침 표본이 극히 적어 안정적인 성능 추정으로 해석하지 않는다.\n'
   text+=table(['seed','모델','N','support>0 클래스','Macro-F1(%)','Accuracy(%)'],overlap_rows)+'\n</details>\n'
  text+='### 같은 seed로 짝지은 핵심 비교\n\n각 숫자는 F1의 절대 **%p 차이**다. seed별 차이를 모두 보이며, 별도 유의성 검정은 수행하지 않았다.\n'
  diffs=[]
  for month in f['evaluation_months']:
   for a,b in [('M2','M1'),('M4','M3'),('M5','M3'),('M5','M4'),('M2','M5')]:
    vv=[100*(by[month,a,s]['groups']['all']['macro_f1']-by[month,b,s]['groups']['all']['macro_f1'])for s in seeds]
    diffs.append([month,a+'−'+b,*[f'{v:+.3f}'for v in vv],ms(vv)])
  text+=table(['월','차이',*map(str,seeds),'평균±SD(%p)'],diffs)
  aprloss=[100*(by['202504','M2',s]['groups']['all']['macro_f1']-by['202504','M5',s]['groups']['all']['macro_f1'])for s in seeds]
  summary['april_teacher_student_loss_pp']=aprloss
  summary['april_loss_mean_pp']=st.mean(aprloss)
  text+=f"성능 목표(M2 대비 M5 감소2%p 이내):4월 평균 감소 **{st.mean(aprloss):.3f}%p**, 개별 반복에서2%p 이내는 **{sum(x<=2 for x in aprloss)}/5**다. 평균 기준 판정과 반복별 안정성을 분리한다. 파라미터는695,593→20,180으로약34.47배 감소했다.\n\n"
  for month in f['evaluation_months']:
   rows=[];cls=records[0]['classes']
   for i,c in enumerate(cls):
    rows.append([c,by[month,'M0',seeds[0]]['groups']['all']['support'][i],*[f"{st.mean(by[month,m,s]['groups']['all']['per_class_f1'][i]for s in seeds)*100:.3f}"for m in models]])
   text+=f'<details><summary>{month} 서비스별 All 평균F1·support</summary>\n\n'+table(['서비스','월별 평가 행 수',*models],rows)+'\n</details>\n'
  text+='지표 재계산에 필요한 행ID·정답·예측라벨·정답 log확률·최대확률을 보존했다. 전송량 절약을 위해 전체20차원 확률벡터는 보존하지 않았으며, 체크포인트와 입력에서 재생성할 수 있다. 원본 예측·전체 혼동행렬·precision/recall·고정 클래스 순서는 평가 원장에 연결돼 있다.\n\n'
 else:text+='\n**월별 평가 결과는 아직 로컬 검증·등록 전이다.** 학습 완료를 시간차 평가 완료로 표시하지 않는다.\n\n'
 bp=E/'main_cpu_benchmark';br=[]
 for p in sorted(bp.glob('*/benchmark.json')):
  r=json.loads(p.read_text());match=next(x for x in train['records']if x['model']==r['model']and x['seed']==r['seed'])
  if r['checkpoint_sha256']!=match['checkpoint_sha256']:raise ValueError('CPU checkpoint mismatch')
  br.append(r)
 text+='### 로컬 CPU 비용 측정\n\n'
 if len(br)==30:
  assert len({(r['model'],r['seed']) for r in br})==30
  assert len({r['input_ids_sha256']for r in br})==1
  assert len({r['benchmark_source_sha256']for r in br})==1
  summary['cpu_benchmark_complete']=True
  text+='모델마다 독립된 새 프로세스를 사용했다. CPU1스레드·FP32,20서비스에서6~7개씩 선정한 공통128입력, batch1 warm-up100회 후1,000회, batch128 warm-up10회 후100회를 측정했다. batch1은128입력을 순환한다. 모델별 표는5개 실행의 중앙값/개별p95/처리량을 각각 평균한 값이다. p95의 평균은 전체 측정값을 합친 하나의p95가 아니다.\n\n'
  rows=[]
  for m in models:
   rr=[x for x in br if x['model']==m]
   rows.append([m,ms([x['batch1']['median_ms']for x in rr]),ms([x['batch1']['p95_ms']for x in rr]),ms([x['batch128']['flows_per_second']for x in rr]),ms([x['inference_file_bytes']/1024**2 for x in rr]),ms([x['memory']['warmed_rss_bytes']/1024**2 for x in rr]),ms([x['memory']['process_peak_rss_bytes']/1024**2 for x in rr])])
  text+=table(['모델','batch1 중앙값 평균±SD(ms)','개별p95 평균±SD(ms)','128묶음 flows/s 평균±SD','추론가중치파일MiB 평균±SD','warm RSS MiB 평균±SD','독립process peak MiB 평균±SD'],rows)
  text+='NN은 내부 고정변환·embedding을 포함한 logits forward, M0는16통계 추출과 확률 예측을 포함한 시간을 주 수치로 사용했다. 파일 로딩·canonicalization·numpy→tensor 준비·패킷 관측 대기는 제외한다. 실시간 네트워크 end-to-end 지연이 아니다. RSS/peak는 라이브러리·할당자·입력 등을 포함한 프로세스 수치로 모델 고유 메모리와 같지 않다. M0의 통계 추출/forward 분해, raw1,000회 지연, baseline/loaded/warm RSS는 원본에 보존했다.\n\n'
  env=br[0]['environment'];text+='측정 환경: `'+json.dumps(env,ensure_ascii=False)+'`.\n\n'
  text+=f'[CPU 측정 원본 폴더]({link(bp)}) 및 실행 코드 main_cpu_benchmark.py에 측정 범위와 반복을 기록했다.\n\n'
 else:text+=f'현재 로컬 등록 **{len(br)}/30**. 전체 비교 완료 전에는 최종 CPU 우위를 선언하지 않는다.\n\n'
 text+='### 해석 범위와 다음 단계\n\n대표 조건의 완료 여부는 학습30·월별60·CPU30을 각각 구분한다. 50/100/1000개 라벨 예산, non-Google13/Google-only20, FLOWSTATS, 학생 구조 변경, 실시간 수집 시연은 이 실행에 포함하지 않았다. 4·5월은 과거 연구에서 이미 본 월이므로 완전히 미사용 외부 최종 테스트라고 부르지 않는다. 현재 고정 설계에서는 시간차 평가로 사용했고 그 점수로 설정을 다시 선택하지 않았다.\n\n'
 extra=H/'main_interpretation.md'
 if extra.exists():text+=extra.read_text()
 (H/'main_analysis_notes.md').write_text(text)
 summary_path=E/'main_recovered/main_summary.json';temp=summary_path.with_suffix('.tmp')
 temp.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');temp.replace(summary_path)
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':run()
