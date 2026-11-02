"""Build the living report from protocol, immutable snapshots and verified results."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib,json,math,subprocess
import numpy as np
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
EXP=ROOT/'experiments/2026-10-30_midterm_restart'
cfg=json.loads((EXP/'config.json').read_text())
manifest=json.loads((EXP/'prepared/manifest.json').read_text())
arch=json.loads((HERE/'snapshots/architecture.json').read_text())
now=datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds')
def rel(path): return '../../'+str(path.relative_to(ROOT))
def table(headers,rows):
    return '\n|'+'|'.join(headers)+'|\n|'+'|'.join(['---']*len(headers))+'|\n'+''.join('|'+'|'.join(str(x).replace('|','/') for x in row)+'|\n' for row in rows)+'\n'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
summary=[]; detail=[]; label_access=[]
for name,co in manifest['cohorts'].items():
    clean=co['january_curation']; cls=co['classes']
    summary.append([name,len(cls),f"{clean['input_rows']:,}",f"{clean['conflicting_rows']:,}",clean['same_label_duplicate_excess'],f"{clean['retained_unique_inputs']:,}",min(clean['retained_per_class'].values()),sum(co['validation_support']),co['evaluation_202504']['rows'],co['evaluation_202505']['rows']])
    rows=[[i,s,co['codes'][i],co['month_support']['202501'][i],clean['retained_per_class'][s],co['validation_support'][i],co['month_support']['202504'][i],co['month_support']['202505'][i]] for i,s in enumerate(cls)]
    detail.append('<details><summary>'+name+' — 서비스별 원본·정제·평가 support와 출력 순서</summary>\n\n'+table(['출력index','서비스','APP코드','1월원본','정제고유','2월검증','4월전체','5월전체'],rows)+'\n</details>\n')
    dev=[]; main=[]
    for phase,seeds,dest in [('development',cfg['development_seeds'],dev),('main',cfg['main_seeds'],main)]:
        for seed in seeds:
            with np.load(EXP/'prepared'/name/f'{phase}_seed{seed}.npz',allow_pickle=False) as f: dest.append(f['id'])
    label_access.append([name,clean['label_access_rows'],len(np.unique(np.concatenate(dev))),len(np.unique(np.concatenate(main))),len(np.unique(np.concatenate(dev+main))),sum(co['validation_support'])])
    ov=[]
    for month in ['202504','202505']:
        g=co['evaluation_'+month]['groups']
        overlap=[g[f'seed{s}_n200_train_overlap'] for s in cfg['main_seeds']]
        ov.append([month,co['evaluation_'+month]['rows'],g['common_unseen'],g['validation_overlap'],g['short_flow'],', '.join(map(str,overlap))])
    detail.append('<details><summary>'+name+' — 평가 마스크 표본수(성능 아님)</summary>\n\n'+table(['월','All','Common-unseen','검증입력겹침','<30패킷','200개학습겹침(seed201~205)'],ov)+'\n</details>\n')
data=table(['구성','클래스','1월원본','충돌제외행','같은라벨중복초과','정제후고유','최소/서비스','2월검증','4월','5월'],summary)+''.join(detail)
data+='\n**라벨 접근과 준비된 표본의 고유 source ID 수:** 아래 main 수는 아직 모두 학습한 수가 아니라 준비한5seed 최대1000 목록의 합집합이다. 정제 라벨 접근과 fitting 라벨을 섞지 않는다.\n'
data+=table(['구성','1월정제라벨접근','개발2seed고유ID','main5seed최대목록고유ID','dev+main고유ID','고정검증라벨'],label_access)
architecture=table(['모델','20클래스총파라미터','학습가능파라미터','첫 forward 출력'],[[k,v['parameters'],v['trainable_parameters'],v['output_shape']] for k,v in arch['models'].items()])
architecture+='\nM4/M5는 M3 구조를 공유한다. 교사 일반식은 `686613 + 449×C`, 학생은 `18880 + 65×C`다. 아래 구조 출력은 학습 전 introspection이며 성능 측정이 아니다.\n'
for k in ['M1','M2','M3']:
    v=arch['models'][k]
    architecture+=f'<details><summary>{k} 실제 생성 모듈·층별 shape·직접 파라미터 수</summary>\n\n'
    architecture+=table(['모듈','종류','입력shape','출력shape'],[[t['module'],t['type'],t['input_shapes'],t['output_shape']] for t in v['forward_trace']])
    architecture+=table(['leaf module','종류','직접파라미터'],[[m['name'],m['type'],m['parameters_direct']] for m in v['modules']])
    architecture+='\n```text\n'+v['repr']+'\n```\n\n</details>\n'
registry=json.loads((HERE/'result_registry.json').read_text()) if (HERE/'result_registry.json').exists() else {'campaigns':[]}
# Multiple recovered snapshots of one campaign are versions, not additional fits.
latest={}
for entry in registry['campaigns']:
    key=entry['campaign_started_utc']
    if key not in latest or entry['imported_at']>latest[key]['imported_at']: latest[key]=entry
campaigns=[json.loads((ROOT/e['verification']).read_text()) for e in latest.values()]
if not campaigns:
    status=f'**문서 갱신: {now}.** 설계·데이터 준비·CPU 연결 점검은 기록됨. A100 개발60회는22:14:14 KST 시작한 상태이며 **로컬에서 검증·등록한 결과 ZIP은 아직0개**다. 이 문서는 실시간 모니터가 아니며 등록 전 점수를 최종결과로 표시하지 않는다. 본 실험·4/5월평가는 미등록이다.'
    ledger='## 검증된 결과 원장\n\n현재 결과 ZIP의 로컬 회수·검증을 기다리고 있다. 아래 빈 상태는0점/실험실패를 뜻하지 않는다. 진행 로그의 임시 점수는 결과표에 복사하지 않는다.\n\n'
else:
    total=sum(len(c['records']) for c in campaigns)
    status=f'**문서 갱신: {now}.** 로컬 무결성·계약 검증을 통과한 개발 결과는{len(campaigns)}개 캠페인, {total}개fit이다. 같은캠페인의중간회수본은중복집계하지않는다. **모두2월개발결과이며 본 실험·4/5월성능이 아니다.**'
    ledger='## 검증된 결과 원장 — 2월 개발 전용\n\n'
    for entry,c in zip(latest.values(),campaigns):
        ledger+=f"### 개발 캠페인 {c['runtime']['started_utc']}\n\n상태 **{c['campaign_status']['state']}**, 검증된fit **{len(c['records'])}/60**. [무결성·실행별 원본 지표 JSON]({rel(ROOT/entry['verification'])}). ZIP SHA256 `{c['archive_sha256']}`. 전체파일검증수{c['verified_files']}개.\n\n"
        if c['selection']:
            s=c['selection']; selected=s['selected']
            ledger+='선택값: '+', '.join(f'{k}={v:g}' for k,v in selected.items())+f"; 공통 KD α={s['kd']['alpha']}, T={s['kd']['temperature']}. 이 개발 캠페인 종료 시점에는 50epoch 동결 전이었다. 이후 곡선 검토·본실험 동결과 실행 결과는 아래 별도 본실험 절에 기록한다.\n\n"
            chosen=[r for r in c['records'] if (r['model'] in selected and (r['num_leaves'] if r['model']=='M0' else r['lr'])==selected[r['model']]) or (r['model'] in ['M4','M5'] and r['alpha']==s['kd']['alpha'] and r['temperature']==s['kd']['temperature'])]
            selected_rows=[]
            for kind in ['M0','M1','M2','M3','M4','M5']:
                rr=sorted([r for r in chosen if r['model']==kind],key=lambda r:r['seed'])
                selected_rows.append([kind,', '.join(f"{r['validation']['macro_f1']*100:.3f}" for r in rr),f"{np.mean([r['validation']['macro_f1'] for r in rr])*100:.3f}",', '.join(str(r['selected_step']) for r in rr),', '.join('예' if r['terminal_trend']['best_at_final_step'] else '아니오' for r in rr)])
            ledger+=table(['모델','seed101·102 검증Macro-F1(%)','개발평균(%)','선택epoch/round','마지막step선택?'],selected_rows)
            pairs=[]
            for seed in cfg['development_seeds']:
                rr={r['model']:r for r in chosen if r['seed']==seed}
                pairs.append([seed,f"{100*(rr['M5']['validation']['macro_f1']-rr['M3']['validation']['macro_f1']):+.3f}",f"{100*(rr['M5']['validation']['macro_f1']-rr['M4']['validation']['macro_f1']):+.3f}"])
            ledger+=table(['개발seed','M5−M3(%p)','M5−M4(%p)'],pairs)
            ledger+='이 표는 선택에 사용한 검증셋 점수다. 최종 성능의 불편 추정치가 아니며5회 본 평가 표를 대체하지 않는다. 학습곡선·하위 서비스 오류·추가 학습 비용을 해석한 뒤 본 설정을 동결해야 한다.\n\n'
        ledger+='<details><summary>전체 후보 실행별 결과 — 좋은 결과와 나쁜 결과 모두</summary>\n\n'
        ledger+=table(['run','val F1(%)','Accuracy(%)','GT CE','선택step','완료step','fit구간초','교사예측초','best파일MiB'],[[f"[{r['run_id']}]({rel(ROOT/r['source_metrics'])})",f"{r['validation']['macro_f1']*100:.3f}",f"{r['validation']['accuracy']*100:.3f}",f"{r['validation']['gt_cross_entropy']:.5f}",r['selected_step'],r['completed_steps'],f"{r['elapsed_seconds']:.2f}",r['teacher_prediction_seconds'] if r['teacher_prediction_seconds'] is not None else '해당없음',f"{r['checkpoint_bytes']/1024**2:.2f}"] for r in c['records']])
        ledger+='\nfit 구간 초는 코드의 타이머 범위이며 원격 실행 전체 벽시계 시간과 동일하지 않다. epoch별 곡선·클래스 precision/recall/F1·혼동행렬·체크포인트 해시는 위 JSON에 전량 보존한다.\n\n</details>\n'
        ledger+='미완료checkpoint: '+(', '.join(c['partial_checkpoints']) if c['partial_checkpoints'] else '없음')+'\n\n'
notes=HERE/'analysis_notes.md'
if notes.exists(): ledger+='\n'+notes.read_text()
main_notes=HERE/'main_analysis_notes.md'
if main_notes.exists(): ledger+='\n'+main_notes.read_text()
continuation_notes=HERE/'continuation_notes.md'
if continuation_notes.exists(): ledger+='\n'+continuation_notes.read_text()
for name in ['continuation_results.md','continuation_interpretation.md','midterm_handoff.md','same_month_evaluation_notes.md']:
    p=HERE/name
    if p.exists():ledger+='\n'+p.read_text()
main_summary_path=EXP/'main_recovered/main_summary.json'
main_summary=json.loads(main_summary_path.read_text()) if main_summary_path.exists() else None
if main_summary:
    monthly='60/60 검증 완료' if main_summary['monthly_evaluation_complete'] else '평가·검증 진행 중'
    cpu='30/30 측정 완료' if main_summary['cpu_benchmark_complete'] else '측정 진행 중'
    release_path=EXP/'main_recovered/runtime_release.json'
    gpu='해제 확인' if release_path.exists() else '해제 증빙 등록 전'
    status=f'**문서 갱신: {now}.** 개발60fit과 별도로 대표 본실험 학습 **30/30 검증 완료**, 4·5월 평가 **{monthly}**, 로컬 CPU **{cpu}**. A100 **{gpu}**. 아래 개발 결과와 본실험 결과를 분리해서 기록한다. 다른 라벨 예산·서비스 구성 확장은 이번 실행에 포함하지 않았다.'
continuation_snapshot_path=EXP/'continuation_status_snapshot.json'
continuation_snapshot=json.loads(continuation_snapshot_path.read_text()) if continuation_snapshot_path.exists() else None
if continuation_snapshot:
    c=continuation_snapshot
    release_path=EXP/'continuation_recovered/runtime_release.json'
    release=json.loads(release_path.read_text()) if release_path.exists() else {}
    if release.get('released'):
        status+=f" **후속 150회 캠페인:** 학습 150개와 신경망 월별 평가 250개를 로컬 회수·검증했고, {release['released_utc']}에 해당 A100을 해제했다. 남은 M0 월별 평가 50개·후속 모델 150개의 CPU 측정·통합 해석은 로컬 후처리 상태를 따른다. 이 문구는 전체 후처리 완료를 뜻하지 않는다."
    else:
        status+=f" **별도 후속150회 캠페인:** {c['observed_utc']} 관측 시 원격 학습{c['completed']}/150, 신경망 월별평가{c['evaluations_completed']}/250, 로컬 검증학습{c['locally_verified_fits']}/150. 이는 실시간 표시가 아니며 회수 전 결과는 미등록이다. 위 A100 해제는 대표200개 캠페인에 대한 기록이며 현재 후속 실행의 GPU 상태와 구분한다."
completion_path=EXP/'continuation_recovered/completion.json'
completion=json.loads(completion_path.read_text()) if completion_path.exists() else None
if completion and completion.get('experiments_complete'):
    review='결과 해석·발표 흐름·Q&A 검토도 완료했다.' if completion.get('analysis_reviewed') else '수치 집계 이후 결과 해석 검토가 남아 있다.'
    status=f'**문서 갱신: {now}.** 개발 60fit, 고정 본실험 180fit(대표 30 + 후속 150), 4·5월 360평가, 180모델 CPU 비용 측정을 검증했다. A100 해제 증빙을 보존했다. {review} **대표 조건의 교사 대비 학생 F1 손실은 21.028%p로, 성능 보존 목표는 미달이다.** CPU 시연은 저장된 공개 PPI 재생이며 실제 네트워크 수집은 별도다. 선택 확장·새 환경 검증·학교 발표 양식 적용 및 제출은 후속 범위로 구분한다.'
content=(HERE/'protocol.md').read_text()
for tag,value in [('CURRENT_STATUS',status),('DATA_TABLES',data),('ARCHITECTURE_TABLES',architecture),('RESULT_LEDGER',ledger)]:
    content=content.replace('<!-- '+tag+' -->',value)
if completion and completion.get('experiments_complete'):
    replacements={
      '개발60회, 대표 본학습30회,4·5월60평가,CPU30모델 측정은 완료하고 원본을 검증했습니다.':'개발60회와 별도로 본학습180회(대표30+후속150),4·5월360평가,CPU180모델 측정을 완료하고 원본을 검증했습니다.',
      '| 최종5회평균·부분집합·CPU비용 | 대표조건 완료 | 본학습30·월별60·CPU30 및 검증 원장 | 다른 라벨 예산·서비스 구성·실시간 비용은 별도 |':'| 최종5회평균·부분집합·CPU비용 | 필수6조건 완료 | 본학습180·월별360·CPU180 및 검증원장 | 실제네트워크수집 지연·선택확장은 별도 |',
      '| M0~M5 본 실험·5회 | 대표200개 조건30fit 검증 완료 | 개발60회와 별개; 다른 예산·구성은 미실행 |':'| M0~M5 본 실험·5회 | 대표30+후속150=180fit 검증 완료 | 혼합20의50/100/200/1000 및 비Google13·Google전용20의200개 |',
      '| 4·5월 성능 | 60평가 회수·지표 재계산 완료 | 전체·학습겹침·비겹침·공통미관측, 클래스별 결과 보존 |':'| 4·5월 성능 | 360평가 회수·지표 검증 완료 | 전체·겹침·비겹침·공통미관측 및 클래스별 결과 보존 |',
      '| CPU 지연·처리량·메모리 | 최종30모델 측정·검증 완료 | Apple M5 CPU1스레드·FP32; 실시간 수집 지연은 제외 |':'| CPU 지연·처리량·메모리 | 본모델180개 측정·검증 완료 | 동일로컬CPU1·FP32 프로토콜; 실시간수집대기는 제외 |',
      '| 실시간 CPU 시연 | 별도 구현·검증 필요 | 저장PPI forward와 실제 수집 시연 구별 |':'| CPU 시연 | 저장공개PPI 재생 구현·예측·브라우저 점검 | 실제네트워크수집시연은 별도검증 |',
      '남은 것은 다른 라벨 예산·서비스 구성, 현재 학생의 큰 성능 격차 원인, 실시간 시연과 새 환경 검증입니다.':'후속 라벨 예산·서비스 구성 비교와 CPU 재생 시연까지 진행했습니다. 남은 것은 학생의 격차 원인 분리, 실제 패킷 수집 시연과 새 환경 검증입니다.'}
    for old,new in replacements.items():content=content.replace(old,new)
(HERE/'research_record.md').write_text(content)
evidence={'generated_at':now,'scope':'Documentation build; no fitting/test-score computation','protocol_sha256':sha(HERE/'protocol.md'),'config_sha256':sha(EXP/'config.json'),'prepared_manifest_sha256':sha(EXP/'prepared/manifest.json'),'architecture_sha256':sha(HERE/'snapshots/architecture.json'),'registered_campaigns':list(latest.values()),'main_summary':main_summary,'continuation_snapshot':continuation_snapshot,'completion':completion,'research_record_md_sha256':sha(HERE/'research_record.md')}
(HERE/'record_evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
node='/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
subprocess.run([node,str(HERE/'render.mjs')],check=True)
print(json.dumps(dict(html=str(HERE/'research_record.html'),characters=len(content),verified_campaigns=len(campaigns)),ensure_ascii=False))
