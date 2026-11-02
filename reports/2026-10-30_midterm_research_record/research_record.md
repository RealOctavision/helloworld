# 중간발표 연구 원장 — PPI 전용 M0~M5 재실험

이 문서는 **설계 이유 → 승인된 선택 → 실제 구현 → 실행 원본 → 결과 → 해석 → 남은 검증**을 연결하는 중간발표 기준 문서다. 새 결과는 검증된 회수 파일에서 자동 집계하고, 과거 탐색 결과는 별도 보관한다. 빈칸을 추측으로 채우지 않는다. ‘승인’, ‘구현’, ‘짧은 점검 통과’, ‘개발 실험 완료’, ‘본 실험 완료’는 서로 다른 상태다.

> 발표 원칙: 방어 가능한 주장은 증거의 범위 안에서 한다. 실험의 한계가 없다고 주장하는 대신, 무엇을 통제했고 무엇이 아직 확인되지 않았는지 답할 수 있어야 한다.

**문서 갱신: 2026-11-02T15:18:18+09:00.** 개발 60fit, 고정 본실험 180fit(대표 30 + 후속 150), 4·5월 360평가, 180모델 CPU 비용 측정을 검증했다. A100 해제 증빙을 보존했다. 결과 해석·발표 흐름·Q&A 검토도 완료했다. **대표 조건의 교사 대비 학생 F1 손실은 21.028%p로, 성능 보존 목표는 미달이다.** CPU 시연은 저장된 공개 PPI 재생이며 실제 네트워크 수집은 별도다. 선택 확장·새 환경 검증·학교 발표 양식 적용 및 제출은 후속 범위로 구분한다.

**별도 확대 재실행 완료(2026-11-02):** [데이터·epoch 확대48개 보고서 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts) · [원본 회수 검증 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts) · [A100 해제 기록 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts). 학습48/48, 월별144평가, CPU48모델, 합성 크기 검사384건을 완료했다. 기존180fit과 별도 캠페인이며 위 본실험 수치에 합산하지 않는다. Google의 수량 대응 Q1 조건이1월 전용보다4·5월에서 크게 개선됐지만,2seed·Q1 정제·기관측 평가월의 한계를 함께 읽는다. 최대1,000epoch 조건도 실제로는200~230epoch에서 조기종료됐다.

**이후 본실험 승인·동결(2026-10-30):** 사용자의 “바로 진행” 승인 후 [main_frozen.json](../../experiments/2026-10-30_midterm_restart/main_frozen.json)을 학습·평가 전에 확정했다. 선택 LR·공통 α0.5/T1·50epoch, 대표200개·seed201~205만 적용한다. 원래 config.json은 준비 데이터와 개발 결과의 해시 보존을 위해 변경하지 않았고, 실행기가 별도 동결 파일을 검증한 뒤 메모리상의 epochs_frozen만 true로 적용한다. 각 fit의 run_context.json과 전체 ZIP에 동결 파일 SHA를 기록한다. 아래 개발 회수 분석의 “본실험 전” 표현은 당시 상태다. 최신 본실험 결과는 본실험 절을 따른다.

## 1. 연구 질문과 중간발표 범위

우리의 중심 질문은 **공개 사전학습으로 적은 목표 라벨에서 더 좋은 교사를 만들 수 있는가, 그 교사의 예측을 이용하면 작은 학생을 직접 학습하는 것보다 유리한가, 그 이득이 시간 변화와 CPU 비용까지 고려해도 남는가**다. 암호화 내용을 복호화하거나 모든 서비스·공격을 자동 판별하는 시스템을 만들었다는 주장이 아니다.

이번 과제는 미리 정한 서비스 중 하나를 예측하는 **폐쇄형 서비스 분류**다. Background는 제외한다. 미등록 서비스 탐지, 악성 여부 판별, 이상 탐지의 완성은 이번 M0~M5 비교로 입증하지 않는다. 계획서 제목에 이상 탐지가 포함되어 있어도 현재 구현 범위를 넓혀 설명하지 않는다.

| 연구 질문 | 비교 | 관찰할 것 | 허용하지 않는 해석 |
|---|---|---|---|
| 사전학습 교사를 활용할 실익이 있는가? | M2 대 M1 | 같은 목표 데이터에서 교사 성능·적응 비용 | BN 정책·선택 LR도 다르므로 초기 가중치 하나의 순수 인과효과라고 단정 |
| 작은 모델은 교사 없이 충분한가? | M3 대 M0·M1·M2 | 직접학습 성능, 크기, CPU 비용 | 학생이 작으므로 반드시 느리거나 부정확하다는 가정 |
| 증류 자체가 도움이 되는가? | M4−M3 | 직접학습 교사 확률을 더한 차이 | 단일 seed의 작은 차이만으로 안정적 우위 주장 |
| 사전학습 교사의 지식이 학생에 도움이 되는가? | **M5−M3**, M5−M4 | 반복별 차이와 평균·표준편차 | 개발셋 최고 점수를 최종 평가 점수로 제시 |
| 작은 학생이 교사를 어느 정도 대체하는가? | M5 대 M2 | 성능 손실·파라미터·지연·학습 비용 | 파라미터 감소율을 실제 속도 향상률로 치환 |
| 시간·라벨 수에 따라 효과가 유지되는가? | 4월/5월, 50/100/200/1000 | 분포 변화와 데이터 효율 | 조건별 최고 설정을 새로 고른 뒤 같은 설정 실험처럼 설명 |

대표 본 실험은 **Google 포함 혼합20, 클래스당 200개, 2025년 4월, 5회 반복**이다. 이 조건은 결과를 본 뒤 바꾸지 않는다. 5월은 시간 변화 평가다. 계획서의 목표는 대표 조건에서 M2 대비 M5의 Macro-F1 감소 2%p 이내, 파라미터 5배 이상 축소, CPU 지연 감소다. **이번 본실험은 크기 축소와 지정 CPU의 batch1 지연 감소를 확인했으나, 성능 손실은 평균21.028%p로2%p 목표를 달성하지 못했다.** 세부 수치와 측정 범위는 본실험 결과 절을 따른다.

## 2. 이전 탐색과 이번 재실험의 관계

초기 A100 탐색, 교사 확대·자체 사전학습, 학생 조정, 6/20서비스 확장, 교사 라벨·정답·확률 분리, 직접학습 학생 비교는 연구 방향을 고르는 탐색 근거로 보존한다. 이번에는 계획서의 M0~M5, 동일한 관측 정보, 라벨 예산, 명시적 정제·분할·반복 조건으로 다시 비교한다.

과거의 S/R/A/B/C/D/E와 이번 M0~M5는 이름만 바꾸어 같은 실행으로 취급하지 않는다. 학생 크기, 교사 출처, 학습 라벨 수, 데이터·전처리·장비가 달라질 수 있다. 특히 과거의 약5만 파라미터 학생과 현재 **20,180개 학생**을 혼용하지 않는다. 과거 결과를 현재 5회 반복에 합산하거나, 과거 높은 수치를 새 정제 데이터 결과로 옮기지 않는다.

- [과거 실험 보관함 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts): 원본 실험 폴더, 이전 보고서와 보존 ZIP 인덱스.
- [계획서 대비 과거 실험 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts): 당시 M0~M5 대응과 기존 결과.
- [데이터 중복 감사 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts): 1~30패킷 비교와 구성별 충돌 진단.
- [재실험 의사결정 원문](../../experiments/2026-10-28_data_audit/restart_decisions.md): 최종 선택은 §8 이후. 이전 절은 당시 검토 이력.

## 3. 결정 이력: 무엇을 왜 선택했는가

날짜는 기록에서 확인되는 일자다. 정확한 시각이 없는 결정에 임의의 시각을 붙이지 않는다. ‘사용자 승인’과 ‘코드 작성 시 정한 구현 기본값’을 구분한다. 이전 선택은 삭제하지 않고 무엇이 대체했는지 남긴다.

| ID | 결정·상태 | 선택 이유·검증할 질문 | 근거·대안 |
|---|---|---|---|
| D01 | 10/28 재실험 분리 | 통제와 재현성을 명시하고 중간발표의 근거를 일관되게 구성 | 사용자 ‘처음부터 다시’ 요청; 이전 실험 보관함 |
| D02 | 최대30 PPI만 사용 | 암호화 내용을 읽지 않는 관측 정보와 공개 교사 호환성 유지 | 5패킷 단독 비교는 현재 범위 제외. 모든 패킷의 개별 시퀀스는 보유 자료에서 확인한 것이 아님 |
| D03 | 30pktTCNET 계열 우선 | 입력 증가 효과와 공개 모델 교체 효과를 한꺼번에 섞지 않음 | mm_cesnet_v2·FLOWSTATS는 후속 |
| D04 | 짧은 플로우 포함 | 중복이 적다는 이유로 긴 플로우만 선택하는 편향 방지 | 패딩·길이별 분석; 사용자 선택6 |
| D05 | 1월 동일 PPI·동일 라벨 대표1개, 충돌 그룹 격리 | 입력 반복 편중과 모호한 학습 대응을 줄임 | 정확도 향상 보장은 없음. min source ID 대표; 라벨 접근량 공개 |
| D06 | 주 평가에 자연 반복 유지 | 실제 월별 분포의 성능과 새로운 입력 성능을 함께 관찰 | ‘평가에서 전부 제거’ 제안을 재검토하여 대체 |
| D07 | 혼합20·200 우선, 50/100/1000 확장 | 대표 조건을 먼저 완성하고 데이터 효율 확인 | 100 조건은 계획서 이후 추가. 50⊂100⊂200⊂1000 |
| D08 | 서비스 자격은 1월 정제 후 ≥1000 | 최대 라벨 예산에서 복제 없이 같은 클래스 비교 | Google-only24→20. non-Google은 자격 충족13 |
| D09 | pooling 직후448→새 분류기 | 선택한 전이 경로를 명확히 하고 불필요한 후단 제거 | refinement와256 neck 제외; 사용자 선택3 |
| D10 | M2 backbone까지 전체 미세조정 | 고정 특징 추출만으로 제한하지 않고 목표 도메인 적응 | BN running 통계 유지와 가중치 동결은 다름 |
| D11 | M1 BN 갱신 / M2 BN 통계 유지 | 각각의 활용 절차를 지정하고 저라벨 미세조정 안정성 검토 | ‘이것이 최선’으로 검증된 설정은 아님; 선택4 |
| D12 | GeM p 학습 가능 | 공식 pooling 구조 유지 | M1 p=3 시작, M2 checkpoint p≈6.28105 시작; 둘 다 학습 |
| D13 | 기본 학생 CNN 하나 | M3/M4/M5의 학습 신호 차이를 비교 | residual/dilated B안은 시간 여유 시/중간 이후 |
| D14 | 학생 고정 변환 | 각 조건의 추정 통계가 달라지는 요인을 줄이고 일관된 입력 | 구체 상수1500/65000은 공개 범위에 맞춘 구현 기본값 |
| D15 | 공통 2월 검증 최대200/서비스 | 평가로 설정을 고르는 누수 방지, 검증 규모 고정 | 부족하면 전량; Hangouts133. 복제 안 함 |
| D16 | LR 소수 후보, 학생 LR은 M3 기준 | 교사별 적응 허용, 학생 학습 신호 비교 통제 | 후보·고정값은 config에 기록; 최적 보장 없음 |
| D17 | 50epoch 개발 후보 후 공통 길이 동결 | 짧은 점검으로 수렴을 가정하지 않음 | 개발 곡선 검토 후 main_frozen.json에서50으로 확정 |
| D18 | 공통 α·T, 9조합×2교사×2개발 seed | 교사마다 다른 KD 설정을 골라 비교가 섞이는 것을 줄임 | 4개 학생 검증 F1 평균으로 공동 선택 |
| D19 | 개발2회와 본 실험5회 분리 | 선택과 결과 추정의 역할을 나눔 | seed101/102와201~205는 구현 명세의 구체 번호 |
| D20 | 대표 조건에서 고른 설정 재사용 | 조건마다 설정을 재탐색하는 비용과 비교 복잡도 제한 | 각 라벨 수·구성별 최적 모델이라는 주장은 하지 않음 |
| D21 | A100 실행 승인(10/30) | CPU 개발 예상시간을 줄임 | 기존 T4 우선 정책을 사용자 요청으로 변경; 데이터·FP32·배치 유지 |
| D22 | 결과와 근거를 지속 기록(10/30) | 팀·교수·멘토가 처음 보아도 추적 가능하게 함 | 본 원장·원본 파일·기계 판독 결과 목록·Q&A 연결 |

**새 결정의 기록 양식:** 질문 → 고려한 대안 → 선택 → 이유 → 결정 주체·일자 → 바뀌는 조건 → 기존 실행에 미치는 영향 → 적용 시작 run → 근거 경로. 결과를 본 뒤 바꾼 것은 사전 결정처럼 쓰지 않는다.

## 4. 데이터 출처·라벨·서비스 구성

목표 자료는 로컬 **CESNET-QUICEXT-25-XS.h5**다. 자료의 전체 제공 기간은 2024-06~2025-05이며, 현재 학습·검증·평가는 아래의 특정 월만 사용한다. 원 자료 전체 규모, 로컬 XS 전체 규모, 감사에서 선택한 서비스 기록 수, 실제 fitting 수는 서로 다르다. 사용한 HDF5 파일·감사 cache·준비 파일의 SHA256을 보존한다.

라벨은 데이터셋이 제공하는 서비스 APP 라벨을 사용한다. 사용자가 특정 앱을 열어 수집한 모든 통신을 그 앱의 정답이라고 붙인 자체 실측 과제가 아니다. Google 서비스 분류도 자료의 라벨 정의 안에서 해석한다. 원본 도메인·SNI·주소 자체는 모델 입력에서 제외한다. 라벨 생성에 쓰인 정보와 모델에 제공한 정보를 구분해야 한다.

**클래스 구성은 원 계획서와 조정된 부분이다.** 원 계획서의 ‘1월 빈도순20’과 지금의 Google 포함 혼합20 목록을 동일하다고 쓰지 않는다. 사용자 요청에 따라 Google 내부 구분을 포함한 명시적 목록을 고정했고, 1월 정제 후 각 서비스 ≥1000을 다시 확인했다. 후속 월 성능에 따라 클래스를 빼거나 교체하지 않는다. 기존 감사에서 여러 월의 분포·충돌을 이미 보았으므로 서비스 선택을 완전한 맹검 결정이라고 설명하지 않는다.


|구성|클래스|1월원본|충돌제외행|같은라벨중복초과|정제후고유|최소/서비스|2월검증|4월|5월|
|---|---|---|---|---|---|---|---|---|---|
|google_included20|20|567,806|6,528|533|560,745|1173|4000|379194|365258|
|non_google13|13|233,433|432|10175|222,826|1858|2600|252471|225067|
|google_only20|20|456,690|6,306|357|450,027|1034|3933|237389|233986|

<details><summary>google_included20 — 서비스별 원본·정제·평가 support와 출력 순서</summary>


|출력index|서비스|APP코드|1월원본|정제고유|2월검증|4월전체|5월전체|
|---|---|---|---|---|---|---|---|
|0|youtube|14|82344|80741|200|60171|61631|
|1|instagram|31|34775|34769|200|53247|45256|
|2|tiktok|35|11451|11392|200|11933|13193|
|3|snapchat|36|50007|49865|200|57813|53748|
|4|spotify|48|16429|16183|200|17181|16916|
|5|discord|50|5034|5032|200|5770|6035|
|6|google-www|1|32849|32362|200|22292|22661|
|7|google-play|2|72703|72542|200|12556|12307|
|8|google-services|3|29999|29682|200|16790|16838|
|9|google-gstatic|4|36884|36134|200|16310|15724|
|10|google-usercontent|5|22056|21883|200|19125|18222|
|11|google-authentication|6|12046|11918|200|7616|6976|
|12|google-fonts|8|17358|16559|200|7884|7762|
|13|google-drive|9|1238|1190|200|511|504|
|14|google-docs|10|1310|1302|200|973|879|
|15|google-translate|13|1373|1365|200|518|466|
|16|google-ads|16|112841|110983|200|41712|39760|
|17|google-safebrowsing|17|5953|5948|200|1657|1587|
|18|google-imasdk|20|1310|1173|200|551|640|
|19|google-calendar|21|19846|19722|200|24584|24153|


</details>
<details><summary>google_included20 — 평가 마스크 표본수(성능 아님)</summary>


|월|All|Common-unseen|검증입력겹침|<30패킷|200개학습겹침(seed201~205)|
|---|---|---|---|---|---|
|202504|379194|376465|2644|149978|5, 1, 0, 5, 7|
|202505|365258|362640|2531|143176|3, 2, 4, 4, 6|


</details>
<details><summary>non_google13 — 서비스별 원본·정제·평가 support와 출력 순서</summary>


|출력index|서비스|APP코드|1월원본|정제고유|2월검증|4월전체|5월전체|
|---|---|---|---|---|---|---|---|
|0|snapchat|36|50007|49872|200|57813|53748|
|1|apple-privaterelay|40|42185|32263|200|17001|17680|
|2|facebook-graph|25|36206|36115|200|51424|40486|
|3|instagram|31|34775|34769|200|53247|45256|
|4|spotify|48|16429|16177|200|17181|16916|
|5|facebook-media|26|12685|12668|200|14312|11620|
|6|facebook-web|27|12305|12252|200|16175|13415|
|7|tiktok|35|11451|11392|200|11933|13193|
|8|discord|50|5034|5032|200|5770|6035|
|9|whatsapp|32|4133|4133|200|1563|1482|
|10|unitygames|37|3937|3900|200|4104|3489|
|11|openx|43|2419|2395|200|598|568|
|12|facebook-connect|28|1867|1858|200|1350|1179|


</details>
<details><summary>non_google13 — 평가 마스크 표본수(성능 아님)</summary>


|월|All|Common-unseen|검증입력겹침|<30패킷|200개학습겹침(seed201~205)|
|---|---|---|---|---|---|
|202504|252471|251691|399|103208|28, 22, 12, 10, 6|
|202505|225067|223930|538|92529|31, 15, 12, 11, 5|


</details>
<details><summary>google_only20 — 서비스별 원본·정제·평가 support와 출력 순서</summary>


|출력index|서비스|APP코드|1월원본|정제고유|2월검증|4월전체|5월전체|
|---|---|---|---|---|---|---|---|
|0|google-www|1|32849|32362|200|22292|22661|
|1|google-play|2|72703|72542|200|12556|12307|
|2|google-services|3|29999|29683|200|16790|16838|
|3|google-gstatic|4|36884|36134|200|16310|15724|
|4|google-usercontent|5|22056|21883|200|19125|18222|
|5|google-authentication|6|12046|11918|200|7616|6976|
|6|google-fonts|8|17358|16558|200|7884|7762|
|7|google-drive|9|1238|1190|200|511|504|
|8|google-docs|10|1310|1302|200|973|879|
|9|google-photos|11|1792|1772|200|331|361|
|10|google-translate|13|1373|1365|200|518|466|
|11|youtube|14|82344|80743|200|60171|61631|
|12|google-hangouts|15|1193|1187|133|62|61|
|13|google-ads|16|112841|110983|200|41712|39760|
|14|google-safebrowsing|17|5953|5948|200|1657|1587|
|15|google-recaptcha|18|1081|1071|200|1016|992|
|16|google-imasdk|20|1310|1173|200|551|640|
|17|google-calendar|21|19846|19723|200|24584|24153|
|18|google-autofill|22|1034|1034|200|532|543|
|19|firebase-crashlytics|23|1480|1456|200|2198|1919|


</details>
<details><summary>google_only20 — 평가 마스크 표본수(성능 아님)</summary>


|월|All|Common-unseen|검증입력겹침|<30패킷|200개학습겹침(seed201~205)|
|---|---|---|---|---|---|
|202504|237389|235128|2230|92895|1, 1, 1, 6, 2|
|202505|233986|232107|1840|89955|5, 1, 2, 3, 5|


</details>

**라벨 접근과 준비된 표본의 고유 source ID 수:** 아래 main 수는 아직 모두 학습한 수가 아니라 준비한5seed 최대1000 목록의 합집합이다. 정제 라벨 접근과 fitting 라벨을 섞지 않는다.

|구성|1월정제라벨접근|개발2seed고유ID|main5seed최대목록고유ID|dev+main고유ID|고정검증라벨|
|---|---|---|---|---|---|
|google_included20|567806|7831|76495|81436|4000|
|non_google13|233433|5110|49460|52279|2600|
|google_only20|456690|7690|61566|65055|3933|



### 4.1 시간 분할과 샘플링

| 역할 | 기간 | 선정 방식 | 허용되는 사용 |
|---|---|---|---|
| 학습 후보·정제 | 2025년1월 | 서비스 목록 고정 후 정확 PPI 정제 | 학습 표본 선정·라벨 예산 구성 |
| 개발 검증 | 2025년2월 | 서비스당 최대200, 고정seed20261030 | LR·KD·best checkpoint·개발 곡선 판단 |
| 대표 평가 | 2025년4월 | 선택 서비스의 유효 기록 전체, 자연 빈도 유지 | 동결한 모델의 시간차 성능 |
| 후속 평가 | 2025년5월 | 같은 규칙 | 시간 변화에 대한 유지 여부 |

한 seed 안에서 최대1000개의 클래스별 고유 입력을 먼저 선택하고 `rank < budget`으로 50/100/200/1000을 만든다. 모델마다 새로 추출하지 않는다. 개발seed101/102는 클래스당200까지만 준비한다. 모델과 라벨 수가 바뀌어도 2월 검증은 공통이다. 반복seed는 표본 선정과 모델 초기화·shuffle도 바꾸므로, 반복 변동은 ‘초기값만의 효과’가 아니다.

4·5월은 과거 실험에서도 본 자료다. 이번 재실험의 설정 선택에는 사용하지 않지만, 프로젝트 전체 관점의 완전 미사용 최종 테스트라고 부르지 않는다. 새로운 수집 시기·환경에서의 검증은 별도 후속 과제다.

### 4.2 정답을 얼마나 사용했는가

‘200개/클래스’는 해당 모델의 **fitting 정답**이며 혼합20이면4000개다. 하지만 정제를 위해 1월 후보 전체의 라벨을 읽었고, 설정 선택에 2월 검증 라벨과 대표200 조건의 개발 학습을 사용한다. 이것을 모두 합쳐 연구 전체에4000개의 라벨만 주어졌다고 말하지 않는다. 50개 조건도 ‘개발 과정 전체가50개만 사용’한 실험이 아니다. M4/M5는 동일한 학습 입력에 교사 확률을 더하며, 이번 기본 실험에 추가 무라벨 풀을 넣지 않는다.

## 5. 중복·충돌·누수 처리의 정확한 범위

흐름은 **자료에서 선택 → 채널 순서·단위·clip·패딩 정규화 → 1월 안에서 입력 그룹화 → 라벨 충돌 격리 → 같은 라벨 대표 선택 → 클래스 자격 확인 → seed별 균등 추출**이다.

1. 키는 라벨·ID·FLOWSTATS를 제외한 canonical PPI `[3,30]`의 little-endian int32 90개, 총360바이트다. `np.void V360`의 전체 바이트 비교를 사용한다. 일부 값만 반올림하거나 체크하지 않은 해시 일치만으로 병합하지 않는다.
2. 같은 키·같은 라벨 그룹에서는 **가장 작은 원본 ID**를 대표로 남긴다. 선택이 임의로 바뀌지 않게 고정하며 그룹 크기와 제외 내역도 저장한다.
3. 같은 키·서로 다른 라벨이면 그룹 전체를 학습에서 제외한다. 다수 라벨로 고쳐 쓰거나 특정 서비스에 유리하게 하나를 남기지 않는다.
4. 이 처리는 라벨 오류 정정이라고 단정하지 않는다. 실제 다른 통신이 제한된 관측 정보에서는 동일할 수도 있다. 중복 제거가 분포를 바꾸며 성능 향상을 보장하지 않는다.
5. 2월·4월·5월 라벨로 1월 정제 대상을 정하지 않는다. 평가의 자연 반복·라벨 충돌은 주 결과에서 지우지 않는다.
6. 동일 source ID의 분할 간 중복은 검사한다. 같은 통신 세션이 여러 ID로 나타나는지, 공개 사전학습 원천과 겹치는지까지 증명한 것은 아니다.

**입력 중복과 모델 표현 중복은 다르다.** 교사는 IPT를 bin으로 나누므로 서로 다른 IPT가 같은 임베딩으로 들어갈 수 있다. M0의 통계도 서로 다른 시퀀스를 같은16차원 값으로 요약할 수 있다. canonical PPI가 고유하다는 말이 모든 모델의 내부 특징이 고유하거나 클래스가 완벽히 분리된다는 뜻은 아니다.

원 자료의 30개 이후 개별 패킷 시퀀스를 모두 읽어 ‘전체 패킷을 보면 중복이0’임을 입증하지 않았다. 이전 FLOWSTATS 결합 충돌 감사도 특정 요약 특징 조합에 대한 결과다.

### 5.1 평가 부분집합

| 이름 | 정확한 정의 | 비교 시 주의 |
|---|---|---|
| All | 해당 평가 월·클래스의 전체 유효 기록 | 주 결과, 자연 빈도 유지 |
| Train-overlap | 이번 seed·budget의 실제 fitting PPI 중 하나와 같은 평가 입력 | 모델 간 같은 seed/budget이면 공통, seed/budget이 바뀌면 달라짐 |
| Train-nonoverlap | All에서 위 overlap 제외 | 검증셋·다른seed 입력과도 전부 다른 집합은 아님 |
| Common-unseen | 사전 지정 main5seeds 최대1000 + dev2seeds200 + 고정val의 PPI 합집합 어디에도 없는 평가 입력 | 라벨 예산·seed 사이 공통 비교용. 사용하지 않은1월 전체 풀을 제외하지 않음 |
| Short/long | 실제 유효 패킷 수<30 / ≥30 | 관측 길이별 보조 분석, 별도 학습이 필요하지 않음 |

입력 겹침은 **라벨을 보지 않고** 정한다. 겹침 집합이 극히 작거나 비어 있을 수 있으므로 N·클래스별 support를 같이 보이고 빈 집합은 N/A다. 표본 수가 작은 overlap 점수만으로 일반적 암기 효과를 주장하지 않는다. 신규·재등장 분해는 같은 평가 예측에서 계산하므로 별도 재학습 수로 세지 않는다.

## 6. 실제 입력 계약

| 항목 | 구현값 |
|---|---|
| 모양·순서 | `[batch,3,30]`, **IPT_ms → DIR → SIZE_bytes** |
| 관측 범위 | 처음 최대30패킷, 별도 첫1초 crop 없음 |
| IPT | ms, 0~65000 clip. 실제0ms도 유효한 값 |
| DIR | 유효 +1/−1, 패딩0 |
| SIZE | 유효 위치1~1500 bytes clip, 패딩0 |
| 유효 마스크 | DIR≠0에서 계산, 채널 제거 전에 보존 |
| 패딩 | 모든 채널0, 짧은 플로우 포함 |
| 제외 입력 | 서비스 정답·교사 확률·SNI·IP·포트·도메인 문자열·전체 FLOWSTATS |

학생의 고정 변환은 `[log1p(IPT)/log1p(65000), DIR, SIZE/1500]`이다. 평균·표준편차를 전체 데이터에서 추정하지 않는다. 교사는 공개 모델의 단위와 내부 embedding 처리를 사용한다. 즉 **같은 관측 정보**를 주지만 교사·학생이 수치 표현까지 같은 것은 아니다. 특히 학생에 교사 확률·정답을 ‘입력 채널’로 붙이지 않는다. 그 정보는 학습 손실에서만 사용한다.

## 7. M0~M5 전체 지도

| 모델 | 구조 계열 | 시작점 | 학습 신호 | 추론 시 교사 필요 |
|---|---|---|---|---|
| M0 | 16통계→LightGBM | 새 트리 학습 | 실제 정답 | 아니오 |
| M1 | 큰 residual CNN 교사 | 공개 학습 가중치 미사용 | CE | 아니오 |
| M2 | M1과 같은 교사 구조 | 공개 가중치로 시작, 전체 미세조정 | CE | 아니오 |
| M3 | 작은 3층 CNN | 새 초기값 | CE | 아니오 |
| M4 | M3과 같은 학생 | M3와 같은 초기값 | GT CE + M1의 soft KD | 학습 때만 |
| M5 | M3과 같은 학생 | M3와 같은 초기값 | GT CE + M2의 soft KD | 학습 때만 |

여섯 모델은 서로 다른 신경망 구조 여섯 종류가 아니다. **트리1계열 + 교사1구조의2학습방식 + 학생1구조의3학습방식**이다. M3/M4/M5는 구조·크기·초기값·데이터·기본 일정이 같고 교사 신호만 달라진다. 모든 모델의 출력 클래스 순서는 동일하다.

## 8. M0 — 통계 특징과 학습하는 트리

M0도 학습한다. 정해진 수작업 규칙을 실행하는 모델이 아니다. LightGBM이 정답을 이용해 특징 분기 기준과 leaf 예측값을 학습하고, boosting 단계마다 앞선 오차를 보완한다. 현재 CPU1스레드로 fitting한다. 신경망의 GPU 학습과 CPU 추론 비용 비교는 서로 다른 단계다.

16개 특징의 **실제 순서**는 아래와 같다. 모두 첫 최대30패킷의 유효 위치에서 계산한다.

1. `packet_count`: 유효 패킷 수.
2. `forward_count`: DIR=+1 개수.
3. `reverse_count`: DIR=−1 개수.
4. `direction_changes`: 유효한 인접 패킷에서 방향이 바뀐 횟수.
5. `size_mean`, `size_std`, `size_min`, `size_max`, `size_sum`, `size_median`.
6. `ipt_mean`, `ipt_std`, `ipt_min`, `ipt_max`, `ipt_sum`, `ipt_median`.

표준편차는 ddof=0이다. 패딩은 제외하되 유효 패킷의0ms는 포함한다. IPT 합은 관측 구간의 간격 합이며 전체 flow DURATION이 아니다. 처음 IPT가0이면 최소 IPT의 정보가 제한될 수 있다는 점도 명시한다. 같은16특징을 고정해 비교하며 평가 결과를 보고 사후 제거하지 않는다.

고정 설정은 multiclass 목적, learning_rate0.05, max_rounds500, patience30, min_data_in_leaf20, lambda_l2=1, deterministic=True, force_col_wise=True, num_threads1이다. `num_leaves ∈ {7,15,31}`만 현재 개발 탐색한다. 검증 Macro-F1로 조기종료하고 기록된 후보 중 F1→낮은CE→이른iteration 기준의 모델을 저장한다. 신경망50epoch와 트리500round는 같은 계산량을 뜻하지 않는다. 실제 선택 round·트리 수·시간·파일 크기를 따로 기록한다. 트리에 신경망과 같은 정의의 파라미터 수를 임의로 붙이지 않는다.

## 9. M1·M2 — 공개 교사에서 실제로 사용한 구조

공개 생성자는 `cesnet-models==0.4.1`의 `model_30pktTCNET_256`이다. 공개 wrapper는256차원 embedding을 출력하지만, **이번 분류기는 256차원 출력을 그대로 사용하지 않는다.** `backbone`에서 feature refinement를 제거하고 global pooling 직후448차원에 새로운 C클래스 Linear를 붙인다. 코드에서 `mlp_shared=Identity`, `use_mlp_shared=False`다. wrapper의256 neck도 사용하지 않는다.

```text
PPI [B,3,30]
  ├─ SIZE embedding: 1501 × 20  → [B,30,20]
  ├─ IPT bucketize + embedding: 200 × 10 → [B,30,10]
  └─ 방향 two-hot: DIR>0, DIR<0 → [B,30,2]
       연결 후 [B,32,30]
  → residual bottleneck 32→192   (중간48, kernel7)
  → residual bottleneck 192→256  (중간64, kernel7)
  → residual bottleneck 256→384  (중간96, kernel5)
  → residual bottleneck 384→448  (중간112, kernel3)
  → learnable GeM → [B,448]
  → 새 Linear(448,C) → [B,C] logits
```

각 bottleneck은 1×1 축소→중앙 kernel 합성곱→1×1 확장과 skip projection을 가진다. stride는 모두1이므로 패킷 축 길이30을 유지한다. 합성곱 bias는 없고 BN과 ReLU가 사용된다. block의 drop_path 모듈은 실제 패키지 구현상 첫 block Identity, 이후 Dropout p≈0.1/0.2/0.3이다. 이를 별도 확률적 깊이 알고리즘이라고 단정하지 않는다. 정확한 모듈 표현과 forward shape는 [architecture.json](snapshots/architecture.json)에 보존했다.

GeM은 각 채널의 패킷 위치 정보를 하나로 집계하는 일반화 평균이다. p가 학습 가능한 스칼라다. 이번 checkpoint를 실제 읽어 확인한 시작값은 M1=3, M2≈6.281049이다. 두 모델의 p를3으로 강제 통일하거나 고정하지 않는다. 교사의 pooling에는 학생과 같은 별도 masked mean을 추가하지 않고 공식 경로를 유지한다. 패딩 처리는 구조 차이의 일부다.

### 9.1 공개 가중치와 원천

사용 파일은 `30pktTCNET_256_CESNET_QUIC22_Week46_Domains.pth`, SHA256은 `dc4b3333388239ac25b8c028c922965e2333cc151dd5fad951950099e86fabc4`다. 로컬 공식 메타데이터는 CESNET-QUIC22, ORIG, W-2022-46을 명시한다. 계획서의 연구 기반은 *Universal Embedding Function for Traffic Classification via QUIC Domain Recognition Pretraining: A Transfer Learning Success*와 공식 CESNET Models/tc-transfer다. 이번 기록은 그 논문의 모든 실험을 재현했다는 뜻이 아니다.

M2는 공개 state를 strict load하고, 원래 학습용 `arcface_module.W`를 제거한 뒤 필요한 backbone을 재사용한다. 목표20서비스 head는 새로 초기화한다. 현재 목표 학습은 CE 분류이며 원천의 전체 사전학습 목적·데이터 규모를 그대로 재실행하지 않는다. 이번 M1은 이전에 자체 사전학습한 더 큰 교사가 아니다.

M1은 공개 학습 가중치를 로드하지 않지만 모든 수치가 완전 무작위인 것은 아니다. 공식 생성자의 **데이터 비의존 PLE 임베딩 초기화**는 유지하며 CNN 등은 생성자 초기화에서 시작한다. PLE는 숫자 구간의 상대 위치를 지정하는 초기 표현이며 목표/사전학습 데이터에서 학습한 checkpoint와 다르다. IPT bin 경계200개도 구조 snapshot에 남겼다. bin화로 정보가 합쳐질 수 있다는 한계를 함께 기록한다.

### 9.2 BN 정책·학습 가능 상태

- M1: `train()`에서 BN running mean/variance를 갱신한다.
- M2: backbone을 포함한 가중치 전체를 학습하되 BN 모듈만 eval 상태로 두어 running statistics를 유지한다. BN affine γ·β는 여전히 학습한다. dropout을 포함해 모델 전체를 eval로 고정한 것이 아니다.
- M1/M2 모두 GeM p와 embedding을 학습 가능하게 유지한다.
- 공식 보조 패킷 크기 히스토그램 counter는 CPU의 `histc(Int)` 호환성 문제 때문에 비활성화했다. 이번 forward·손실에 쓰지 않는 카운터이며, 미관측 embedding 교체 기능도 사용하지 않는다. 초기 실패를 보존했고 파라미터 수는 변하지 않았다.

따라서 M2−M1은 **명시한 적응 절차를 포함한 사전학습 활용 비교**다. 초기 가중치 하나만 바꾸는 엄밀한 단일요인 ablation은 아니다. 이 차이를 발표에서 숨기지 않는다.


|모델|20클래스총파라미터|학습가능파라미터|첫 forward 출력|
|---|---|---|---|
|M1|695593|695593|[2, 20]|
|M2|695593|695593|[2, 20]|
|M3|20180|20180|[2, 20]|


M4/M5는 M3 구조를 공유한다. 교사 일반식은 `686613 + 449×C`, 학생은 `18880 + 65×C`다. 아래 구조 출력은 학습 전 introspection이며 성능 측정이 아니다.
<details><summary>M1 실제 생성 모듈·층별 shape·직접 파라미터 수</summary>


|모듈|종류|입력shape|출력shape|
|---|---|---|---|
|backbone.packet_size_nn_embedding|Embedding|[[2, 30]]|[2, 30, 20]|
|backbone.packet_ipt_nn_embedding|Embedding|[[2, 30]]|[2, 30, 10]|
|backbone.cnn_ppi.0|Bottleneck|[[2, 32, 30]]|[2, 192, 30]|
|backbone.cnn_ppi.1|Bottleneck|[[2, 192, 30]]|[2, 256, 30]|
|backbone.cnn_ppi.2|Bottleneck|[[2, 256, 30]]|[2, 384, 30]|
|backbone.cnn_ppi.3|Bottleneck|[[2, 384, 30]]|[2, 448, 30]|
|backbone.cnn_ppi|Sequential|[[2, 32, 30]]|[2, 448, 30]|
|backbone.cnn_ppi_global_pool|Sequential|[[2, 448, 30]]|[2, 448]|
|head|Linear|[[2, 448]]|[2, 20]|


|leaf module|종류|직접파라미터|
|---|---|---|
|backbone.cnn_ppi_stem|Identity|0|
|backbone.packet_size_nn_embedding|Embedding|30020|
|backbone.packet_ipt_nn_embedding|Embedding|2000|
|backbone.cnn_ppi.0.downsample.0|Identity|0|
|backbone.cnn_ppi.0.downsample.1|PadConv1d|6144|
|backbone.cnn_ppi.0.downsample.2|BatchNorm1d|384|
|backbone.cnn_ppi.0.conv1|PadConv1d|1536|
|backbone.cnn_ppi.0.norm1|BatchNorm1d|96|
|backbone.cnn_ppi.0.conv2|PadConv1d|16128|
|backbone.cnn_ppi.0.norm2|BatchNorm1d|96|
|backbone.cnn_ppi.0.conv3|PadConv1d|9216|
|backbone.cnn_ppi.0.norm3|BatchNorm1d|384|
|backbone.cnn_ppi.0.act|ReLU|0|
|backbone.cnn_ppi.0.drop_path|Identity|0|
|backbone.cnn_ppi.1.downsample.0|Identity|0|
|backbone.cnn_ppi.1.downsample.1|PadConv1d|49152|
|backbone.cnn_ppi.1.downsample.2|BatchNorm1d|512|
|backbone.cnn_ppi.1.conv1|PadConv1d|12288|
|backbone.cnn_ppi.1.norm1|BatchNorm1d|128|
|backbone.cnn_ppi.1.conv2|PadConv1d|28672|
|backbone.cnn_ppi.1.norm2|BatchNorm1d|128|
|backbone.cnn_ppi.1.conv3|PadConv1d|16384|
|backbone.cnn_ppi.1.norm3|BatchNorm1d|512|
|backbone.cnn_ppi.1.act|ReLU|0|
|backbone.cnn_ppi.1.drop_path|Dropout|0|
|backbone.cnn_ppi.2.downsample.0|Identity|0|
|backbone.cnn_ppi.2.downsample.1|PadConv1d|98304|
|backbone.cnn_ppi.2.downsample.2|BatchNorm1d|768|
|backbone.cnn_ppi.2.conv1|PadConv1d|24576|
|backbone.cnn_ppi.2.norm1|BatchNorm1d|192|
|backbone.cnn_ppi.2.conv2|PadConv1d|46080|
|backbone.cnn_ppi.2.norm2|BatchNorm1d|192|
|backbone.cnn_ppi.2.conv3|PadConv1d|36864|
|backbone.cnn_ppi.2.norm3|BatchNorm1d|768|
|backbone.cnn_ppi.2.act|ReLU|0|
|backbone.cnn_ppi.2.drop_path|Dropout|0|
|backbone.cnn_ppi.3.downsample.0|Identity|0|
|backbone.cnn_ppi.3.downsample.1|PadConv1d|172032|
|backbone.cnn_ppi.3.downsample.2|BatchNorm1d|896|
|backbone.cnn_ppi.3.conv1|PadConv1d|43008|
|backbone.cnn_ppi.3.norm1|BatchNorm1d|224|
|backbone.cnn_ppi.3.conv2|PadConv1d|37632|
|backbone.cnn_ppi.3.norm2|BatchNorm1d|224|
|backbone.cnn_ppi.3.conv3|PadConv1d|50176|
|backbone.cnn_ppi.3.norm3|BatchNorm1d|896|
|backbone.cnn_ppi.3.act|ReLU|0|
|backbone.cnn_ppi.3.drop_path|Dropout|0|
|backbone.cnn_ppi_global_pool.0|AdaptiveGeM|1|
|backbone.cnn_ppi_global_pool.1|Flatten|0|
|backbone.cnn_ppi_global_pool.2|Identity|0|
|backbone.cnn_ppi_global_pool.3|Identity|0|
|backbone.mlp_shared|Identity|0|
|backbone.classifier|Identity|0|
|head|Linear|8980|


```text
Teacher(
  (backbone): Multimodal_CESNET_Enhanced(
    (cnn_ppi_stem): Identity()
    (packet_size_nn_embedding): Embedding(1501, 20, padding_idx=0)
    (packet_ipt_nn_embedding): Embedding(200, 10, padding_idx=0)
    (cnn_ppi): Sequential(
      (0): Bottleneck(
        (downsample): Sequential(
          (0): Identity()
          (1): PadConv1d(32, 192, kernel_size=(1,), stride=(1,), bias=False)
          (2): BatchNorm1d(192, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        )
        (conv1): PadConv1d(32, 48, kernel_size=(1,), stride=(1,), bias=False)
        (norm1): BatchNorm1d(48, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (conv2): PadConv1d(48, 48, kernel_size=(7,), stride=(1,), padding=(3,), bias=False)
        (norm2): BatchNorm1d(48, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (conv3): PadConv1d(48, 192, kernel_size=(1,), stride=(1,), bias=False)
        (norm3): BatchNorm1d(192, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (act): ReLU(inplace=True)
        (drop_path): Identity()
      )
      (1): Bottleneck(
        (downsample): Sequential(
          (0): Identity()
          (1): PadConv1d(192, 256, kernel_size=(1,), stride=(1,), bias=False)
          (2): BatchNorm1d(256, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        )
        (conv1): PadConv1d(192, 64, kernel_size=(1,), stride=(1,), bias=False)
        (norm1): BatchNorm1d(64, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (conv2): PadConv1d(64, 64, kernel_size=(7,), stride=(1,), padding=(3,), bias=False)
        (norm2): BatchNorm1d(64, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (conv3): PadConv1d(64, 256, kernel_size=(1,), stride=(1,), bias=False)
        (norm3): BatchNorm1d(256, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (act): ReLU(inplace=True)
        (drop_path): Dropout(p=0.10000000149011612, inplace=False)
      )
      (2): Bottleneck(
        (downsample): Sequential(
          (0): Identity()
          (1): PadConv1d(256, 384, kernel_size=(1,), stride=(1,), bias=False)
          (2): BatchNorm1d(384, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        )
        (conv1): PadConv1d(256, 96, kernel_size=(1,), stride=(1,), bias=False)
        (norm1): BatchNorm1d(96, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (conv2): PadConv1d(96, 96, kernel_size=(5,), stride=(1,), padding=(2,), bias=False)
        (norm2): BatchNorm1d(96, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (conv3): PadConv1d(96, 384, kernel_size=(1,), stride=(1,), bias=False)
        (norm3): BatchNorm1d(384, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (act): ReLU(inplace=True)
        (drop_path): Dropout(p=0.20000001788139343, inplace=False)
      )
      (3): Bottleneck(
        (downsample): Sequential(
          (0): Identity()
          (1): PadConv1d(384, 448, kernel_size=(1,), stride=(1,), bias=False)
          (2): BatchNorm1d(448, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        )
        (conv1): PadConv1d(384, 112, kernel_size=(1,), stride=(1,), bias=False)
        (norm1): BatchNorm1d(112, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (conv2): PadConv1d(112, 112, kernel_size=(3,), stride=(1,), padding=(1,), bias=False)
        (norm2): BatchNorm1d(112, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (conv3): PadConv1d(112, 448, kernel_size=(1,), stride=(1,), bias=False)
        (norm3): BatchNorm1d(448, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (act): ReLU(inplace=True)
        (drop_path): Dropout(p=0.30000001192092896, inplace=False)
      )
    )
    (cnn_ppi_global_pool): Sequential(
      (0): AdaptiveGeM(p=3.0000, eps=1e-06)
      (1): Flatten(start_dim=1, end_dim=-1)
      (2): Identity()
      (3): Identity()
    )
    (mlp_shared): Identity()
    (classifier): Identity()
  )
  (head): Linear(in_features=448, out_features=20, bias=True)
)
```

</details>
<details><summary>M2 실제 생성 모듈·층별 shape·직접 파라미터 수</summary>


|모듈|종류|입력shape|출력shape|
|---|---|---|---|
|backbone.packet_size_nn_embedding|Embedding|[[2, 30]]|[2, 30, 20]|
|backbone.packet_ipt_nn_embedding|Embedding|[[2, 30]]|[2, 30, 10]|
|backbone.cnn_ppi.0|Bottleneck|[[2, 32, 30]]|[2, 192, 30]|
|backbone.cnn_ppi.1|Bottleneck|[[2, 192, 30]]|[2, 256, 30]|
|backbone.cnn_ppi.2|Bottleneck|[[2, 256, 30]]|[2, 384, 30]|
|backbone.cnn_ppi.3|Bottleneck|[[2, 384, 30]]|[2, 448, 30]|
|backbone.cnn_ppi|Sequential|[[2, 32, 30]]|[2, 448, 30]|
|backbone.cnn_ppi_global_pool|Sequential|[[2, 448, 30]]|[2, 448]|
|head|Linear|[[2, 448]]|[2, 20]|


|leaf module|종류|직접파라미터|
|---|---|---|
|backbone.cnn_ppi_stem|Identity|0|
|backbone.packet_size_nn_embedding|Embedding|30020|
|backbone.packet_ipt_nn_embedding|Embedding|2000|
|backbone.cnn_ppi.0.downsample.0|Identity|0|
|backbone.cnn_ppi.0.downsample.1|PadConv1d|6144|
|backbone.cnn_ppi.0.downsample.2|BatchNorm1d|384|
|backbone.cnn_ppi.0.conv1|PadConv1d|1536|
|backbone.cnn_ppi.0.norm1|BatchNorm1d|96|
|backbone.cnn_ppi.0.conv2|PadConv1d|16128|
|backbone.cnn_ppi.0.norm2|BatchNorm1d|96|
|backbone.cnn_ppi.0.conv3|PadConv1d|9216|
|backbone.cnn_ppi.0.norm3|BatchNorm1d|384|
|backbone.cnn_ppi.0.act|ReLU|0|
|backbone.cnn_ppi.0.drop_path|Identity|0|
|backbone.cnn_ppi.1.downsample.0|Identity|0|
|backbone.cnn_ppi.1.downsample.1|PadConv1d|49152|
|backbone.cnn_ppi.1.downsample.2|BatchNorm1d|512|
|backbone.cnn_ppi.1.conv1|PadConv1d|12288|
|backbone.cnn_ppi.1.norm1|BatchNorm1d|128|
|backbone.cnn_ppi.1.conv2|PadConv1d|28672|
|backbone.cnn_ppi.1.norm2|BatchNorm1d|128|
|backbone.cnn_ppi.1.conv3|PadConv1d|16384|
|backbone.cnn_ppi.1.norm3|BatchNorm1d|512|
|backbone.cnn_ppi.1.act|ReLU|0|
|backbone.cnn_ppi.1.drop_path|Dropout|0|
|backbone.cnn_ppi.2.downsample.0|Identity|0|
|backbone.cnn_ppi.2.downsample.1|PadConv1d|98304|
|backbone.cnn_ppi.2.downsample.2|BatchNorm1d|768|
|backbone.cnn_ppi.2.conv1|PadConv1d|24576|
|backbone.cnn_ppi.2.norm1|BatchNorm1d|192|
|backbone.cnn_ppi.2.conv2|PadConv1d|46080|
|backbone.cnn_ppi.2.norm2|BatchNorm1d|192|
|backbone.cnn_ppi.2.conv3|PadConv1d|36864|
|backbone.cnn_ppi.2.norm3|BatchNorm1d|768|
|backbone.cnn_ppi.2.act|ReLU|0|
|backbone.cnn_ppi.2.drop_path|Dropout|0|
|backbone.cnn_ppi.3.downsample.0|Identity|0|
|backbone.cnn_ppi.3.downsample.1|PadConv1d|172032|
|backbone.cnn_ppi.3.downsample.2|BatchNorm1d|896|
|backbone.cnn_ppi.3.conv1|PadConv1d|43008|
|backbone.cnn_ppi.3.norm1|BatchNorm1d|224|
|backbone.cnn_ppi.3.conv2|PadConv1d|37632|
|backbone.cnn_ppi.3.norm2|BatchNorm1d|224|
|backbone.cnn_ppi.3.conv3|PadConv1d|50176|
|backbone.cnn_ppi.3.norm3|BatchNorm1d|896|
|backbone.cnn_ppi.3.act|ReLU|0|
|backbone.cnn_ppi.3.drop_path|Dropout|0|
|backbone.cnn_ppi_global_pool.0|AdaptiveGeM|1|
|backbone.cnn_ppi_global_pool.1|Flatten|0|
|backbone.cnn_ppi_global_pool.2|Identity|0|
|backbone.cnn_ppi_global_pool.3|Identity|0|
|backbone.mlp_shared|Identity|0|
|backbone.classifier|Identity|0|
|head|Linear|8980|


```text
Teacher(
  (backbone): Multimodal_CESNET_Enhanced(
    (cnn_ppi_stem): Identity()
    (packet_size_nn_embedding): Embedding(1501, 20, padding_idx=0)
    (packet_ipt_nn_embedding): Embedding(200, 10, padding_idx=0)
    (cnn_ppi): Sequential(
      (0): Bottleneck(
        (downsample): Sequential(
          (0): Identity()
          (1): PadConv1d(32, 192, kernel_size=(1,), stride=(1,), bias=False)
          (2): BatchNorm1d(192, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        )
        (conv1): PadConv1d(32, 48, kernel_size=(1,), stride=(1,), bias=False)
        (norm1): BatchNorm1d(48, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (conv2): PadConv1d(48, 48, kernel_size=(7,), stride=(1,), padding=(3,), bias=False)
        (norm2): BatchNorm1d(48, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (conv3): PadConv1d(48, 192, kernel_size=(1,), stride=(1,), bias=False)
        (norm3): BatchNorm1d(192, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (act): ReLU(inplace=True)
        (drop_path): Identity()
      )
      (1): Bottleneck(
        (downsample): Sequential(
          (0): Identity()
          (1): PadConv1d(192, 256, kernel_size=(1,), stride=(1,), bias=False)
          (2): BatchNorm1d(256, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        )
        (conv1): PadConv1d(192, 64, kernel_size=(1,), stride=(1,), bias=False)
        (norm1): BatchNorm1d(64, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (conv2): PadConv1d(64, 64, kernel_size=(7,), stride=(1,), padding=(3,), bias=False)
        (norm2): BatchNorm1d(64, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (conv3): PadConv1d(64, 256, kernel_size=(1,), stride=(1,), bias=False)
        (norm3): BatchNorm1d(256, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (act): ReLU(inplace=True)
        (drop_path): Dropout(p=0.10000000149011612, inplace=False)
      )
      (2): Bottleneck(
        (downsample): Sequential(
          (0): Identity()
          (1): PadConv1d(256, 384, kernel_size=(1,), stride=(1,), bias=False)
          (2): BatchNorm1d(384, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        )
        (conv1): PadConv1d(256, 96, kernel_size=(1,), stride=(1,), bias=False)
        (norm1): BatchNorm1d(96, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (conv2): PadConv1d(96, 96, kernel_size=(5,), stride=(1,), padding=(2,), bias=False)
        (norm2): BatchNorm1d(96, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (conv3): PadConv1d(96, 384, kernel_size=(1,), stride=(1,), bias=False)
        (norm3): BatchNorm1d(384, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (act): ReLU(inplace=True)
        (drop_path): Dropout(p=0.20000001788139343, inplace=False)
      )
      (3): Bottleneck(
        (downsample): Sequential(
          (0): Identity()
          (1): PadConv1d(384, 448, kernel_size=(1,), stride=(1,), bias=False)
          (2): BatchNorm1d(448, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        )
        (conv1): PadConv1d(384, 112, kernel_size=(1,), stride=(1,), bias=False)
        (norm1): BatchNorm1d(112, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (conv2): PadConv1d(112, 112, kernel_size=(3,), stride=(1,), padding=(1,), bias=False)
        (norm2): BatchNorm1d(112, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (conv3): PadConv1d(112, 448, kernel_size=(1,), stride=(1,), bias=False)
        (norm3): BatchNorm1d(448, eps=1e-05, momentum=0.1, affine=True, bias=True, track_running_stats=True)
        (act): ReLU(inplace=True)
        (drop_path): Dropout(p=0.30000001192092896, inplace=False)
      )
    )
    (cnn_ppi_global_pool): Sequential(
      (0): AdaptiveGeM(p=6.2810, eps=1e-06)
      (1): Flatten(start_dim=1, end_dim=-1)
      (2): Identity()
      (3): Identity()
    )
    (mlp_shared): Identity()
    (classifier): Identity()
  )
  (head): Linear(in_features=448, out_features=20, bias=True)
)
```

</details>
<details><summary>M3 실제 생성 모듈·층별 shape·직접 파라미터 수</summary>


|모듈|종류|입력shape|출력shape|
|---|---|---|---|
|blocks.0|Conv1d|[[2, 3, 30]]|[2, 32, 30]|
|blocks.1|Conv1d|[[2, 32, 30]]|[2, 64, 30]|
|blocks.2|Conv1d|[[2, 64, 30]]|[2, 64, 30]|
|head|Linear|[[2, 64]]|[2, 20]|


|leaf module|종류|직접파라미터|
|---|---|---|
|blocks.0|Conv1d|320|
|blocks.1|Conv1d|6208|
|blocks.2|Conv1d|12352|
|head|Linear|1300|


```text
Student(
  (blocks): ModuleList(
    (0): Conv1d(3, 32, kernel_size=(3,), stride=(1,), padding=(1,))
    (1): Conv1d(32, 64, kernel_size=(3,), stride=(1,), padding=(1,))
    (2): Conv1d(64, 64, kernel_size=(3,), stride=(1,), padding=(1,))
  )
  (head): Linear(in_features=64, out_features=20, bias=True)
)
```

</details>


## 10. M3·M4·M5 — 동일한 작은 학생

```text
PPI [B,3,30] → 고정 변환·원본 DIR 마스크
→ Conv1d(3,32,k3,s1,p1,bias) → ReLU → 패딩 다시0
→ Conv1d(32,64,k3,s1,p1,bias) → ReLU → 패딩 다시0
→ Conv1d(64,64,k3,s1,p1,bias) → ReLU → 패딩 다시0
→ 유효 위치만 평균 [B,64]
→ Linear(64,C,bias) → [B,C] logits
```

BN·dropout·residual·dilation 확장·사전학습 embedding을 넣지 않은 기본 CNN이다. 파라미터 수는 conv320+6208+12352, 20클래스 head1300으로 **20,180개**다. 교사695,593개 대비 약34.47배 작다. 이는 동일한 데이터 관측량에서 작은 분류기가 어느 정도까지 가능한지 확인하기 위한 기준 구조이며 전역 최적 구조를 찾았다는 주장은 아니다.

각 conv 뒤에 다시 마스크를 적용하므로 bias나 인접 연산으로 패딩 위치에 생긴 값을 다음 층에 그대로 전달하지 않는다. 마지막은 패딩을 포함한30칸 평균이 아니라 유효 위치 수로 나눈 평균이다. 단, convolution의 인접 문맥과 경계 효과 자체가 사라진다는 뜻은 아니다.

같은seed의 M3/M4/M5 생성자 seed는 `seed+10000`으로 맞춘다. 학습 RNG는 `seed+30000`, epoch별 순열은 `seed*100000+epoch`로 고정한다. 교사를 생성·예측하면서 학생 RNG가 달라지지 않도록 다시 설정한다. CPU 연결 점검에서는 초기 state hash 일치를 확인했고, 회수된 실제 개발 결과에서도 해당 hash를 대조한다. 서로 다른 장비·PyTorch 버전까지 bitwise 동일함을 보장하는 것은 아니다.

## 11. 손실·증류 설계

M1/M2/M3는 실제 정답 CE로 학습한다. M4/M5는 같은 학생의 출력에 다음 손실을 사용한다.

```text
L = (1 − α) × CE(student_logits, y)
    + α × T² × KL(softmax(teacher_logits/T) || softmax(student_logits/T))
α 후보 = 0.1, 0.25, 0.5
T 후보 = 1, 2, 4
```

CE는 온도를 적용하지 않은 원래 logits로 계산한다. KD에는 T를 적용하며 KL은 teacher→student 방향이고 reduction은 batchmean이다. 교사는 eval·gradient 비활성 상태로 고정하고 동일 학습 입력의 **raw logits**를 예측·저장한다. 학생이 교사 argmax만 따라가는 별도 hard pseudo-label 손실은 현재 기본 비교에 없다. 교사가 틀려도 실제 정답 손실이 함께 있으나 개선이 보장되지는 않는다.

교사는 같은 cohort·classes 순서·seed·budget·phase·train ID/input/label hash·config hash를 가진 checkpoint여야 한다. M4에는 M1, M5에는 M2를 연결한다. 1000개로 학습한 교사를50개 조건 학생에게 몰래 제공하지 않는다. 교사 checkpoint를 고른 정보는2월 검증이며 평가4·5월로 교사를 다시 고르지 않는다.

개발 중 같은seed의 교사 best checkpoint는9개의 α/T 후보에서 재사용한다. 현재 코드는 교사 logits를 각fit에서 다시 계산·저장하므로 동일 교사의 예측 생성 시간도 반복 비용에 포함된다. 공유 cache로 한번만 생성했다고 보고하지 않는다.

## 12. 학습 일정·탐색·선택을 재현하는 규칙

| 항목 | M1 | M2 | M3/M4/M5 |
|---|---|---|---|
| Optimizer | AdamW | AdamW | AdamW |
| LR 후보 | 1e−4 / 3e−4 / 1e−3 | 1e−5 / 3e−5 / 1e−4 | M3:3e−4 / 1e−3 / 3e−3; M4/M5는 M3 선택값 |
| 배치 | 128 | 128 | 128 |
| epoch | 개발 출발 후보50 | 동일 | 동일 |
| weight decay | 모든 학습 파라미터1e−4 | 동일 | 동일 |
| 스케줄 |5epoch warm-up 뒤 cosine 감소 | 동일 | 동일 |
| 수치 | FP32, CUDA TF32 off | 동일 | 동일 |
| 추가 처리 | augmentation·gradient clipping·L2SP·LDIFS·계층별LR 없음 | 동일 | 동일 |

batch128로4000개를 학습하면 epoch당32회 업데이트다. 마지막 배치는32개이며 drop_last로 버리지 않는다. 50epoch면1600회 업데이트다. 같은epoch라도1000개/클래스 조건은 업데이트가 더 많으므로 ‘모든 라벨 수에서 총계산량 동일’이라고 쓰지 않는다. 20클래스의 예산50/100/200/1000은 각각 epoch당8/16/32/157회, 50epoch 가정이면400/800/1600/7850회다.

선택 규칙은 다음 순서다.

1. 각 실행의 best checkpoint: 검증 Macro-F1 최대 → 정확히 동점이면 정답 CE 최소 → 이른epoch.
2. M1/M2/M3 LR 및 M0 leaves: 각 후보의 개발seed101/102 검증 F1 산술평균 최대 → 평균CE 최소 → 후보값이 작은 것(구현의 결정적 동점 처리).
3. M4/M5 공통 KD: 각 α/T에서 두seed×두학생의 검증 F1 네 값 평균 최대 → 평균CE 최소 → 작은α → 작은T.
4. 선택 결과와 개발 학습곡선을 검토한 뒤 본 실험 설정을 동결한다. 원본 config의 `epochs_frozen=false`는 보존한다. 본실험 실행기는 별도의 main_frozen.json 해시·승인 범위를 검증한 경우에만 메모리상 true를 적용한다.

신경망은50epoch 전에 성능이 낮다고 임의 종료하지 않으며 best와last를 따로 저장한다. M0는 명시한 조기종료를 사용한다. 예산 초과·비유한 loss/gradient·데이터 계약 오류는 실패로 기록하고 checkpoint를 보존한다. 실패를0점 성공 실행으로 평균에 넣거나 성공한seed만 남기지 않는다.

현재 `train_loss`는 epoch 내 **batch 평균 손실들의 단순평균**이다. 마지막 batch 크기가 달라 sample-weighted epoch loss와 다를 수 있다. 검증 CE는 전체 검증 logits에서 계산하며 checkpoint 동점 기준으로 사용한다. 개발 곡선의 수치 정의도 함께 보존한다.

## 13. 실행 수와 우선순위

| 단계 | 산식 | 횟수 | 현재 의미 |
|---|---|---:|---|
| CPU 연결 점검 | M0~M5의 짧은 실행 |6모델+복구/계약 점검 | 성능 비교 반복에 포함하지 않음 |
| A100 속도 측정 | M1/M2/M3×2epoch |3 | 최종 성능 아님 |
| 교사/학생 LR 개발 |3모델×3LR×2seed |18 |2월로 선택 |
| M0 개발 |3leaves×2seed |6 |2월로 선택 |
| KD 개발 |2교사×9조합×2seed |36 |공통α/T 선택 |
| **개발 합계** |18+6+36 |**60** | 본 실험 수와 별도 |
| 대표 본 실험 |6모델×5seed, 혼합20·200 |30 | 설정 동결 뒤 |
| 나머지 라벨 예산 |6모델×5seed×3예산 |90추가 | 대표 포함120 |
| 입력 제거 선택 확장 |M3의 제외3종×5seed |15추가 | 여유 시; 전체PPI M3 재사용 |
| 후속 구성 | non-Google13 / Google-only20 |별도 실행표 필요 | 실제 완료 범위 구분 |

우선 대표30회와 분석을 완성한다. 이후 라벨 예산 확장, 시간 여유가 있으면 M3 채널 제거, 후속 서비스 구성 순이다. mm_cesnet_v2·전체FLOWSTATS·MoE·새 학생 구조·자체 대형 사전학습을 이번 개발60회에 추가하지 않는다. 사용자 승인 범위와 후속 아이디어를 구별한다.

## 14. 평가 지표와 발표할 비교

Macro-F1은 서비스별 F1의 산술평균으로, 큰 서비스의 빈도만으로 전체 점수가 높아지는 현상을 줄인다. Accuracy도 함께 보고하며 역할을 구분한다. 혼동행렬은 **행=실제 라벨, 열=예측 라벨**이다. 클래스 순서·support·클래스별 precision/recall/F1을 반드시 함께 보존한다.

각 seed의 M5−M3, M5−M4를 같은 평가 입력에서 짝지어 계산한다. F1이0.70에서0.72면 **+2%p**이며 상대2% 상승과 다르다. 평균만 제시하지 않고5개 차이를 그대로 제시한다. 본 실험 표준편차는 sample SD(ddof=1)로 표시하고,0.01 등의 작은 차이를 통계적 유의성 검증 없이 확정적 우위로 부르지 않는다. 별도 검정·신뢰구간을 계산했다면 단위, 가정, 방법을 명시한다.

부분집합에 특정 클래스의 support가0일 수 있다. 현재 공통 metrics 함수는 고정 C개 클래스에 대해 denominator0의 F1을0으로 처리한다. 빈 부분집합은N/A다. 따라서 subset Macro-F1이 얼마나 많은 클래스를 포함하는지 보여야 한다. 클래스가 존재하는 것만 평균한 수치를 추가하면 다른 지표로 명시하고 사후에 유리한 정의로 주지표를 교체하지 않는다.

Google 관련 혼동은 전체 Macro-F1뿐 아니라 서비스별 support·recall·혼동쌍으로 분석한다. Google 포함20와 미포함13은 클래스 수·종류·난이도가 동시에 달라 Google 여부 하나의 인과효과로 단정하지 않는다. 데이터셋 라벨 정의와 수집 환경의 범위 안에서 결론을 낸다.

## 15. 경량성·실행비용과 CPU 시연

성능과 함께 교사→학생의 파라미터 수, 저장 파일 크기, CPU batch1 중앙값·p95, 묶음 처리량, 메모리를 비교한다. 같은 로컬 CPU·1스레드·FP32·warm-up 조건을 사용하고, 반복 횟수·OS·Python/Torch/LightGBM 버전·CPU 모델을 기록한다. 모델별 독립 메모리 측정과 전체프로세스 peak RSS를 혼동하지 않는다.

시간은 **패킷 관측 대기 → 특징 추출/전처리 → 모델 forward**로 나눈다. 저장된PPI의 forward만 측정한 결과를 네트워크에서 패킷을 기다리는 시간을 포함한 end-to-end 지연으로 말하지 않는다. M0의16통계 추출도 무료로 처리하지 않는다. 교사/학생의 내부 embedding·고정변환이 forward에 포함되는지 측정 코드를 함께 제시한다.

학습 비용은 M1/M2 학습, 교사 logits 생성, 학생 학습, checkpoint/압축, 전송, GPU 유휴 연결 시간을 분리한다. M5 추론에 교사가 필요 없다는 사실이 교사 학습비용이0이라는 뜻은 아니다. A100 단위/시간은 연결 시간에 관한 화면 관측값이며 순수 train epoch 합과 같지 않다.

CPU 연결 점검의 약0.043ms 학생/약0.38ms 교사 수치는2epoch 모델의 예비 측정이다. 최종 모델의 정식 반복 벤치마크로 인용하지 않는다. A100 사용은 학습 속도를 위한 선택이며 CPU 배포 성능을 자동 증명하지 않는다.

## 16. 현재까지 실제로 확인한 것과 오류 이력

- 실제 데이터 manifest를 만들고 클래스 자격·균등/중첩·원본ID 분리·입력 고유성을 검사했다. 원본HDF5와 감사cache는4개월48개 기록을 spot-check했다. 전체 원자료 모든 값을 다시 독립 재검증했다는 뜻은 아니다.
- 평가월별256개 기록/구성에 대해 별도의 Python byte-set 계산으로 overlap 정의를 대조했다. 같은 작성자의 다른 계산 방식이며 독립 연구자 검증이라고 부르지 않는다.
- CPU M0~M5의 실제 입력→학습→저장→재로드→검증 예측 연결을 확인했다. 2epoch/작은 검증의 점수는 성능 결론에서 제외한다.
- M3/M4/M5 초기 hash, M1 BN 갱신·M2 BN 유지, CE와α0의 gradient 일치, 잘못된 교사 metadata 거부, dropout을 포함한 M1 다음 업데이트의 checkpoint 복구 일치를 확인했다.
- 첫 CPU 실행은 공식 보조 `histc(Int)`에서 실패했다. `smoke/`에 보존하고 counter 비활성화 뒤 `smoke_v2/`에서 성공했다.
- 검증셋 자체를 Common-unseen처럼 표기한 연결 점검 주석 오류를 수정했다. 가중치·선택을 바꾸지 않았고 수정 전 보고 hash를 남겼다.
- A100 전송에서 일반 파일 선택 UI가 응답하지 않아8개 base64 조각으로 전송했다. 전체 ZIP hash·CRC·내부10파일 hash 확인 후 실행했다. 전송 방식의 변경은 데이터 변경이 아니다.
- 이번 원장 작성 중 README의 ‘GPU 미실행’ 문구가 최신 A100 시작과 충돌함을 발견해 현재 요약을 수정했다. 원문 snapshot은 보존한다.

CPU검증의 코드 hash는 당시 `training.py`를 가리킨다. 이후 A100 허용·TF32 off·장비 metadata를 추가했으므로 과거 검증파일 하나가 현재 모든 코드를 재검증했다고 쓰지 않는다. GPU 경로는 실제 A100의 짧은 실행과 개발 진행으로 확인하며 최종 결과는 회수 후 별도 무결성·계약 검사한다.

## 17. 이후 결과를 빠뜨리지 않는 기록 규약

기록의 단위는 ‘좋은 최종 모델’만이 아니라 **탐색 후보마다의 실행**이다. 완료·실패·중단·재개·폐기 사유를 구분한다. 동일 실행을 두 번 회수해도 중복 집계하지 않는다. 원본 metrics/체크포인트/예측/로그를 보존한 후 파생 표를 만든다. 값을 수동 복사해 점수 표만 남기지 않는다.

| 묶음 | 반드시 남길 내용 | 지금의 저장 위치/상태 |
|---|---|---|
| 식별 | run ID, phase, cohort, model, seed, label budget | 폴더·metrics·campaign status. M0 일부는 경로/config에서 복원하며 추론 출처 표기 |
| 질문·결정 | 왜 실행했는지, 비교 기준, 승인·변경 이력 | 본 원장·restart_decisions |
| 데이터 | ID목록, 클래스 순서, support, rank, 전처리·분할·입력/라벨hash | prepared/*.npz, manifest, metrics |
| 구조 | 생성자·버전, 실제 모듈, layer shape·param, head·BN·mask·GeM | models.py, snapshots/architecture.json |
| 학습 | LR/optimizer/decay/batch/일정/epoch·update/정밀도 | config·코드snapshot·metrics history·checkpoint |
| 증류 | teacher checkpoint/hash, 같은seed/budget 검증, α/T, logits | metrics·teacher_logits.npz·teacher checkpoint |
| 선택 | 후보 전체 점수, bestepoch, 동점 처리, 공통KD 기준 | selection_partial/selection/kd_grid/metrics |
| 결과 | 전체·클래스·부분집합·혼동행렬, 각epoch, 검증 예측 | metrics·validation_predictions; 본평가60건 compact 예측·4그룹 지표 회수 완료 |
| 재현·복구 | best/last, optimizer/scheduler/CPU·CUDA RNG, 코드hash | 체크포인트와snapshot |
| 환경·비용 | GPU/CPU, 패키지, wall-clock·train/val/teacher 시간, 메모리, 단위 | runtime/metrics/log·pip freeze·nvidia-smi·본fit resources·최종CPU30개 기록 |
| 해석 | 관찰, 가능한 설명, 반례·한계, 주장 가능 범위, 다음 결정 | 결과 회수 요약과 Q&A |
| 무결성 | remote ZIP SHA, local SHA, CRC, 안전경로, 내부 파일hash·완전성 | 회수 verification·등록 ledger |

기록의 빈 부분도 숨기지 않는다. 개발 단계에서 없었던 실행별 CUDA peak allocation은 본실험 resources에 추가했고, 전체 `pip freeze`·GPU driver 상세·평가월 예측·최종 CPU 원본도 회수했다. 다만 학습 batch별 시간 전체, 모든 개별 CPU 측정의 정확한 wall-clock 시작/종료, 호스트 전체 부하·온도 통제, 실시간 수집 시연은 기록·검증하지 않았다. 프로세스 RSS나 CUDA allocation을 장치 전체 전력·메모리 비용과 같다고 말하지 않는다. 근거가 없는 값은 ‘미기록/미측정’으로 남긴다. 이미 돌아가는 학습 코드를 바꿔 다른 조건을 같은 캠페인에 섞지 않는다.

결과 회수 후 아래 도구가 ZIP hash·CRC·경로·내부hash를 검증하고, 실제 학습 ID·클래스·epoch·교사 대응·학생 초기값·선택 규칙을 대조하여 실행별 원장에 등록한다. `validation_predictions.npz`에서 Macro-F1·Accuracy·혼동행렬을 재계산해 metrics와 대조한다. 최종 CE는 logits 기준 저장값이고, softmax 확률의 반올림·underflow 차이 때문에 확률에서 재계산한 CE가 bitwise 같은 값이라고 요구하지 않는다.

```sh
# 회수된 ZIP의 원격 SHA256을 먼저 읽고 기록한 다음 실행
research/2026-09-22_plan_support/.venv/bin/python \
  reports/2026-10-30_midterm_research_record/import_results.py \
  --archive /절대경로/colab_development_results.zip --expected-sha256 원격_SHA256

# 새 원본 결과 등록 후 보고서 재생성
research/2026-09-22_plan_support/.venv/bin/python \
  reports/2026-10-30_midterm_research_record/build_record.py
```

정상 완료뿐 아니라 예산 중단의 부분 결과도 그대로 보존한다. ‘계획60’과 ‘검증완료60’을 구분하며 덜 끝났으면 남은 수를 표시한다. 이미 등록한ZIP은 idempotent 처리한다. **이 기록 도구는 학습을 시작하거나 평가월 점수를 계산하지 않는다.**

대표 본실험은 별도 `verify_main_results.py training/evaluation --archive … --sha256 …`로 검증했다. 학습·평가·CPU 원장은 `experiments/2026-10-30_midterm_restart/main_recovered/`에 보존하고 중앙 result_registry.json의 main_campaigns에 연결했다. `build_main_summary.py`는 검증된 결과를 집계한 뒤 `build_record.py`에 포함한다. 모든 표는 원본을 바꾸지 않는 파생물이다.

## 검증된 결과 원장 — 2월 개발 전용

### 개발 캠페인 2026-10-30T13:14:14Z

상태 **completed**, 검증된fit **60/60**. [무결성·실행별 원본 지표 JSON](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/verified_results.json). ZIP SHA256 `1c41e56d0f3ef16be123da67ec32bcce399ea562568e4200c696ccadda08bc37`. 전체파일검증수357개.

선택값: M1=0.001, M2=0.0001, M3=0.003, M0=31; 공통 KD α=0.5, T=1. 이 개발 캠페인 종료 시점에는 50epoch 동결 전이었다. 이후 곡선 검토·본실험 동결과 실행 결과는 아래 별도 본실험 절에 기록한다.


|모델|seed101·102 검증Macro-F1(%)|개발평균(%)|선택epoch/round|마지막step선택?|
|---|---|---|---|---|
|M0|49.755, 48.318|49.037|91, 137|아니오, 아니오|
|M1|66.832, 67.916|67.374|23, 26|아니오, 아니오|
|M2|69.886, 69.902|69.894|43, 44|아니오, 아니오|
|M3|45.107, 43.296|44.202|36, 40|아니오, 아니오|
|M4|45.341, 43.560|44.451|46, 40|아니오, 아니오|
|M5|45.667, 43.499|44.583|46, 40|아니오, 아니오|


|개발seed|M5−M3(%p)|M5−M4(%p)|
|---|---|---|
|101|+0.560|+0.325|
|102|+0.203|-0.061|

이 표는 선택에 사용한 검증셋 점수다. 최종 성능의 불편 추정치가 아니며5회 본 평가 표를 대체하지 않는다. 학습곡선·하위 서비스 오류·추가 학습 비용을 해석한 뒤 본 설정을 동결해야 한다.

<details><summary>전체 후보 실행별 결과 — 좋은 결과와 나쁜 결과 모두</summary>


|run|val F1(%)|Accuracy(%)|GT CE|선택step|완료step|fit구간초|교사예측초|best파일MiB|
|---|---|---|---|---|---|---|---|---|
|[M0_s101_c15_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M0_s101_c15_a0_t1/metrics.json)|49.125|49.650|1.76311|120|150|4.36|해당없음|3.82|
|[M0_s101_c31_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M0_s101_c31_a0_t1/metrics.json)|49.755|50.200|1.78090|91|121|5.09|해당없음|5.51|
|[M0_s101_c7_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M0_s101_c7_a0_t1/metrics.json)|48.638|49.275|1.78163|263|293|5.94|해당없음|4.44|
|[M0_s102_c15_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M0_s102_c15_a0_t1/metrics.json)|48.281|48.875|1.77205|110|140|4.01|해당없음|3.48|
|[M0_s102_c31_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M0_s102_c31_a0_t1/metrics.json)|48.318|48.600|1.86392|137|167|7.24|해당없음|8.32|
|[M0_s102_c7_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M0_s102_c7_a0_t1/metrics.json)|48.054|48.750|1.78051|219|249|4.88|해당없음|3.68|
|[M1_s101_c0.0001_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M1_s101_c0.0001_a0_t1/metrics.json)|61.752|61.225|1.29687|38|50|41.41|0.0|8.12|
|[M1_s101_c0.0003_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M1_s101_c0.0003_a0_t1/metrics.json)|63.597|63.075|1.44345|25|50|40.86|0.0|8.10|
|[M1_s101_c0.001_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M1_s101_c0.001_a0_t1/metrics.json)|66.832|66.850|1.53135|23|50|41.28|0.0|8.10|
|[M1_s102_c0.0001_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M1_s102_c0.0001_a0_t1/metrics.json)|62.644|61.500|1.35281|34|50|41.24|0.0|8.11|
|[M1_s102_c0.0003_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M1_s102_c0.0003_a0_t1/metrics.json)|64.914|64.025|1.52018|28|50|40.84|0.0|8.11|
|[M1_s102_c0.001_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M1_s102_c0.001_a0_t1/metrics.json)|67.916|67.250|1.60945|26|50|41.18|0.0|8.10|
|[M2_s101_c0.0001_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M2_s101_c0.0001_a0_t1/metrics.json)|69.886|69.750|1.04656|43|50|40.31|0.0|8.13|
|[M2_s101_c1e-05_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M2_s101_c1e-05_a0_t1/metrics.json)|40.509|42.000|2.19967|50|50|41.25|0.0|8.14|
|[M2_s101_c3e-05_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M2_s101_c3e-05_a0_t1/metrics.json)|59.955|59.850|1.35621|41|50|40.47|0.0|8.12|
|[M2_s102_c0.0001_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M2_s102_c0.0001_a0_t1/metrics.json)|69.902|69.625|1.02394|44|50|40.36|0.0|8.13|
|[M2_s102_c1e-05_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M2_s102_c1e-05_a0_t1/metrics.json)|40.891|42.275|2.09538|50|50|41.05|0.0|8.14|
|[M2_s102_c3e-05_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M2_s102_c3e-05_a0_t1/metrics.json)|60.469|60.625|1.32027|45|50|40.68|0.0|8.13|
|[M3_s101_c0.0003_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M3_s101_c0.0003_a0_t1/metrics.json)|19.873|23.500|2.61651|27|50|6.87|0.0|0.28|
|[M3_s101_c0.001_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M3_s101_c0.001_a0_t1/metrics.json)|31.038|34.025|2.25589|37|50|6.89|0.0|0.29|
|[M3_s101_c0.003_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M3_s101_c0.003_a0_t1/metrics.json)|45.107|45.625|1.85910|36|50|6.88|0.0|0.29|
|[M3_s102_c0.0003_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M3_s102_c0.0003_a0_t1/metrics.json)|21.149|24.775|2.60930|44|50|6.92|0.0|0.30|
|[M3_s102_c0.001_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M3_s102_c0.001_a0_t1/metrics.json)|30.318|32.725|2.29456|41|50|6.95|0.0|0.30|
|[M3_s102_c0.003_a0_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M3_s102_c0.003_a0_t1/metrics.json)|43.296|44.250|1.91118|40|50|6.94|0.0|0.30|
|[M4_s101_c0.003_a0.1_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s101_c0.003_a0.1_t1/metrics.json)|45.571|46.375|1.85375|41|50|8.03|0.046289675000025454|0.30|
|[M4_s101_c0.003_a0.1_t2](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s101_c0.003_a0.1_t2/metrics.json)|45.045|45.875|1.88779|43|50|7.68|0.04355335299987928|0.30|
|[M4_s101_c0.003_a0.1_t4](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s101_c0.003_a0.1_t4/metrics.json)|43.940|45.025|1.93492|46|50|7.75|0.04422854399990683|0.31|
|[M4_s101_c0.003_a0.25_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s101_c0.003_a0.25_t1/metrics.json)|45.367|46.200|1.84376|44|50|7.63|0.043629640999824915|0.30|
|[M4_s101_c0.003_a0.25_t2](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s101_c0.003_a0.25_t2/metrics.json)|44.546|45.400|1.96091|50|50|7.74|0.04381851599964648|0.31|
|[M4_s101_c0.003_a0.25_t4](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s101_c0.003_a0.25_t4/metrics.json)|42.264|43.925|2.09743|46|50|7.72|0.04419007800015606|0.31|
|[M4_s101_c0.003_a0.5_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s101_c0.003_a0.5_t1/metrics.json)|45.341|46.200|1.84164|46|50|7.69|0.04372867100028088|0.31|
|[M4_s101_c0.003_a0.5_t2](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s101_c0.003_a0.5_t2/metrics.json)|43.285|44.400|2.06072|46|50|7.80|0.04374336199998652|0.31|
|[M4_s101_c0.003_a0.5_t4](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s101_c0.003_a0.5_t4/metrics.json)|40.898|42.950|2.35518|44|50|7.61|0.04381502800015369|0.30|
|[M4_s102_c0.003_a0.1_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s102_c0.003_a0.1_t1/metrics.json)|43.287|44.275|1.91268|40|50|7.64|0.04361470099956932|0.30|
|[M4_s102_c0.003_a0.1_t2](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s102_c0.003_a0.1_t2/metrics.json)|43.408|44.300|1.95510|40|50|7.67|0.043704810999770416|0.30|
|[M4_s102_c0.003_a0.1_t4](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s102_c0.003_a0.1_t4/metrics.json)|43.034|43.925|1.98404|40|50|7.66|0.0436001960001704|0.30|
|[M4_s102_c0.003_a0.25_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s102_c0.003_a0.25_t1/metrics.json)|43.577|44.675|1.90907|40|50|7.67|0.04361879299995053|0.30|
|[M4_s102_c0.003_a0.25_t2](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s102_c0.003_a0.25_t2/metrics.json)|42.918|43.800|2.03192|40|50|7.65|0.04425458699961382|0.30|
|[M4_s102_c0.003_a0.25_t4](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s102_c0.003_a0.25_t4/metrics.json)|41.613|43.250|2.14311|49|50|7.70|0.043736814000112645|0.31|
|[M4_s102_c0.003_a0.5_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s102_c0.003_a0.5_t1/metrics.json)|43.560|44.575|1.89962|40|50|7.63|0.04373298900009104|0.30|
|[M4_s102_c0.003_a0.5_t2](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s102_c0.003_a0.5_t2/metrics.json)|41.759|42.725|2.15933|40|50|7.82|0.04376528199964014|0.30|
|[M4_s102_c0.003_a0.5_t4](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M4_s102_c0.003_a0.5_t4/metrics.json)|38.530|40.725|2.41521|42|50|7.71|0.043967670000256476|0.30|
|[M5_s101_c0.003_a0.1_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s101_c0.003_a0.1_t1/metrics.json)|45.239|45.975|1.84512|39|50|7.84|0.04386724400001185|0.30|
|[M5_s101_c0.003_a0.1_t2](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s101_c0.003_a0.1_t2/metrics.json)|45.173|46.050|1.85623|46|50|7.84|0.044672412000181794|0.31|
|[M5_s101_c0.003_a0.1_t4](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s101_c0.003_a0.1_t4/metrics.json)|44.842|45.900|1.85335|43|50|7.64|0.043641547999868635|0.30|
|[M5_s101_c0.003_a0.25_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s101_c0.003_a0.25_t1/metrics.json)|45.698|46.525|1.83156|44|50|7.61|0.04366299100001925|0.30|
|[M5_s101_c0.003_a0.25_t2](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s101_c0.003_a0.25_t2/metrics.json)|43.796|44.875|1.89703|43|50|7.66|0.04356921999988117|0.30|
|[M5_s101_c0.003_a0.25_t4](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s101_c0.003_a0.25_t4/metrics.json)|42.502|44.025|1.93137|43|50|7.68|0.04369905200019275|0.30|
|[M5_s101_c0.003_a0.5_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s101_c0.003_a0.5_t1/metrics.json)|45.667|46.550|1.83724|46|50|7.59|0.04386064999971495|0.31|
|[M5_s101_c0.003_a0.5_t2](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s101_c0.003_a0.5_t2/metrics.json)|43.071|44.500|1.95201|46|50|7.64|0.04530064200025663|0.31|
|[M5_s101_c0.003_a0.5_t4](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s101_c0.003_a0.5_t4/metrics.json)|39.393|41.225|2.06871|30|50|7.56|0.04429293900011544|0.29|
|[M5_s102_c0.003_a0.1_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s102_c0.003_a0.1_t1/metrics.json)|43.651|45.150|1.87302|43|50|7.61|0.04386694999993779|0.30|
|[M5_s102_c0.003_a0.1_t2](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s102_c0.003_a0.1_t2/metrics.json)|43.131|44.225|1.91324|40|50|7.65|0.04414484500011895|0.30|
|[M5_s102_c0.003_a0.1_t4](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s102_c0.003_a0.1_t4/metrics.json)|43.150|44.550|1.90678|43|50|7.66|0.04376931599972522|0.30|
|[M5_s102_c0.003_a0.25_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s102_c0.003_a0.25_t1/metrics.json)|43.011|44.250|1.88566|47|50|7.67|0.04444646799993279|0.31|
|[M5_s102_c0.003_a0.25_t2](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s102_c0.003_a0.25_t2/metrics.json)|43.517|44.750|1.92415|40|50|7.64|0.043679805000010674|0.30|
|[M5_s102_c0.003_a0.25_t4](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s102_c0.003_a0.25_t4/metrics.json)|40.188|42.175|1.97921|49|50|7.64|0.04413398699989557|0.31|
|[M5_s102_c0.003_a0.5_t1](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s102_c0.003_a0.5_t1/metrics.json)|43.499|44.600|1.89055|40|50|7.58|0.04364124999983687|0.30|
|[M5_s102_c0.003_a0.5_t2](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s102_c0.003_a0.5_t2/metrics.json)|42.493|44.250|1.95776|46|50|7.71|0.04433702000005724|0.31|
|[M5_s102_c0.003_a0.5_t4](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/extracted/colab_development/fits/M5_s102_c0.003_a0.5_t4/metrics.json)|37.446|40.075|2.09885|43|50|7.64|0.04366106299994499|0.30|


fit 구간 초는 코드의 타이머 범위이며 원격 실행 전체 벽시계 시간과 동일하지 않다. epoch별 곡선·클래스 precision/recall/F1·혼동행렬·체크포인트 해시는 위 JSON에 전량 보존한다.

</details>
미완료checkpoint: 없음


## 회수 후 해석 — 2026-10-30 개발 실험 60회

### 1. 이번에 실제로 끝난 것

**Google 포함 20서비스·클래스당 학습 200개·첫 최대 30패킷 PPI만을 사용한 설정 선택 실험이 완료됐다.** 학습은 2025년 1월, 검증은 2월의 고정 4,000개다. 개발 seed는101/102 두 개이고, 총60fit은 서로 다른 설정을 고르는 후보들이다. 같은 최종 모델을60번 반복한 결과가 아니다. 신경망54fit은 모두50epoch·1,600update를 완료했다. LightGBM6fit은 별도의 최대500round·patience30 규칙을 적용했다. 별도2epoch 속도측정3fit은 성능 비교에서 제외했다.

캠페인 로그 기준 시작은22:14:14 KST, 종합 실행은1,578.95초(26분18.95초)였다. 최종 결과 ZIP304,667,724바이트를 회수했고, 원격·로컬 SHA256, ZIP CRC·안전 경로, 내부357파일 해시,60개metrics, 입력ID/라벨/클래스 순서, 최적 checkpoint 선택, 교사 연결, 학생 초기값을 검증했다. 검증 예측에서 F1·정확도·혼동행렬도 다시 계산하여 원본 지표와 일치함을 확인했다.

일반 브라우저 다운로드의 로컬 저장을 확인하지 못해4MiB 단위73조각으로 회수했다. 모든 조각과 최종 조립본의 해시를 대조했다. 이 과정의 연결 대기시간은26분19초 학습 시간에 포함되지 않는다. GPU 연결 해제 확인 시각은**23:11:03 KST**다. 학습은55분 상한 전에 끝났지만, 파일 보존 때문에 런타임 연결은23:09 목표 시각을 약2분 넘겼다. 이를 비용 준수 성공으로 숨기지 않는다. 초기 잔여 단위와 관측 요율만으로 실제 청구 단위를 확정하지 않으며, 종료 시 잔여 단위는 측정하지 않았다.

원본과 환경 기록:

- [결과 ZIP — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts): SHA256 `1c41e56d0f3ef16be123da67ec32bcce399ea562568e4200c696ccadda08bc37`.
- [실행별 지표·50epoch 곡선·클래스 precision/recall·검증 JSON](../../experiments/2026-10-30_midterm_restart/colab_recovered/1c41e56d0f3ef16b/verified_results.json).
- [환경·전체 로그 ZIP — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts): SHA256 `a4bc1445e0824bd8d4494769f3f4fcd0d869181732b9b0a41741df5116360f02`.
- [pip freeze — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts), [nvidia-smi — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts), [전체 실행 로그 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts), [해제 기록 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts), [비연결 UI 증거 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts).

### 2. 핵심 결과를 어떻게 읽어야 하는가

아래 모든 평균은 **선택에 사용한 2월 검증셋에서 개발seed 두 개의 평균**이다. 아직 최종4월 성능, 5월 시간차 성능, 통계적 유의성을 뜻하지 않는다. Macro-F1은 각 서비스의 F1을 동일 비중으로 평균하므로 정확도와 다른 지표다.

| 모델 | 역할 | 검증 Macro-F1 평균 | 검증 정확도 평균 |
|---|---|---:|---:|
| M0 | PPI 유래16통계·LightGBM |49.037%|49.400%|
| M1 | 공개 학습 가중치 없이 큰 모델 직접학습 |67.374%|67.050%|
| M2 | 공개 사전학습 큰 모델 전체 미세조정 |69.894%|69.688%|
| M3 | 작은 학생 정답 직접학습 |44.202%|44.938%|
| M4 | M1을 교사로 한 학생 KD |44.451%|45.388%|
| M5 | M2를 교사로 한 학생 KD |44.583%|45.575%|

**관찰 A — 사전학습 활용 절차는 큰 모델의 성능을 높였다.** M2−M1은seed101에서+3.055%p, seed102에서+1.986%p, 평균+2.520%p다. 다만 M1과M2는 초기 가중치뿐 아니라 학습률과 BN 통계 처리도 다르다. 따라서 “가중치 하나만 바꿔 정확히2.52%p 개선됐다”는 인과 설명은 과하다. 승인된 두 학습 절차를 비교한 결과다.

**관찰 B — 현재 학생의 차이는 KD만으로 크게 줄지 않았다.** M4−M3은평균+0.249%p, M5−M3은+0.381%p다. 두seed에서M5−M3은각각+0.560/+0.203%p였다. 방향은 양수지만 매우 작은 개발셋 차이이고, 하이퍼파라미터 선택에 같은 검증셋을 사용했다. “증류가 일반적으로 개선한다”거나 “유의한 개선”으로 발표하지 않는다.

**관찰 C — 더 좋은 교사가 더 좋은 학생을 안정적으로 보장하지 않았다.** M5−M4는seed101에서+0.325%p, seed102에서−0.061%p, 평균+0.132%p다. M2는M1보다 두seed 모두 좋았지만, 학생 간 비교에서는 한seed의 순서가 바뀌었다. 강한 교사의 이점이 학생에게 그대로 이전됐다고 말할 수 없다.

**관찰 D — 현재 학생은 크기 목표를 충족해도 성능 목표와 거리가 있다.** M2와M5는각각695,593개/20,180개파라미터로약34.47배차이다. 그러나검증F1차이는평균25.312%p로, 계획서의2%p이내목표와크게다르다. 이 개발 결과는 목표 미달의 경고 신호다. 최종 목표 판정은 정해진 본실험과4월평가로 해야 하며, “압축에 성공했다”라고 성능까지 묶어 결론내리지 않는다.

**관찰 E — 작은 신경망보다 트리 기준선이 높았다.** M0는M3보다평균4.835%p높았다. 같은 관측 구간의 PPI를 사용하지만M0는16개 통계로 변환하고M3는시퀀스를직접처리하므로 입력표현과학습방식이함께달라진비교다. “항상 신경망이 유리하다”는 가정은 지지되지 않는다. 추론 지연·모델 크기·메모리를 같은 조건에서 측정하기 전에는M0가전체적으로우월하다고도단정하지않는다.

현재 학생의 작은 용량, 깊이3의kernel3 CNN(최대 국소 수용영역7패킷), 평균 풀링, 최적화와 시간차 변화 등이 격차의 후보 원인이다. **이번 결과만으로 어느 원인인지 분리하지는 못했다.** 30패킷을 입력받는다는 것과 모델이 임의의 장거리 순서를 충분히 표현한다는 것은 다르다. 향후 구조 변경은 기존 결과를 덮어쓰지 않는 별도 가설 실험이어야 한다.

### 3. 왜 이 설정을 선택했는가

M1 학습률0.001, M2 학습률0.0001, 학생 공통 학습률0.003, M0 num_leaves31이 승인된 후보 중 두 seed 평균 검증 F1로 선택됐다. 동점 처리도 코드의 CE → 더 작은 후보 순서와 대조했다. **모두 현재 후보 범위의 상단값**이다. 따라서 전역 최적값을 찾았다는 뜻은 아니며, 작은 학습률 후보가50epoch에서 덜 학습됐을 가능성도 있다. 이를 이유로 이번 점검 중 후보를 임의로 추가하지 않았다.

공통 KD는 M4/M5 × seed101/102의 네 결과를 함께 평균하여 **α0.5·T1**을 선택했다. 공통 평균 F1은44.517%이며, 이 값은 M5 단독 점수44.583%와 다르다. 개별 최고값을 모델마다 따로 선택하지 않는 규칙을 지켰다. 예를 들어 M4만 보면 α0.25·T1이44.472%로 α0.5·T1의44.451%보다0.021%p 높지만, 사전 합의한 공통 설정이 우선한다.

| T / α | M4 평균 F1 | M5 평균 F1 | 해석 |
|---|---:|---:|---|
|1 / 0.1|44.429%|44.445%|기본 학생보다 작은 개선|
|1 / 0.25|44.472%|44.354%|교사별 최고점과 공통 최고점이 다름|
|1 / 0.5|44.451%|44.583%|선택된 공통 조합|
|2 / 0.5|42.522%|42.782%|T1 대비 낮음|
|4 / 0.5|39.714%|38.420%|높은 온도·비중이 현재 조건에서 악화|

온도를 높여 확률분포를 부드럽게 하면 항상 도움된다는 가정은 지지되지 않는다. 그렇다고 T1이 모든 데이터·학생에서 최적이라고 일반화하지 않는다. 전체9조합 × 두 교사 × 두 seed 결과는 원장에 모두 보존했다.

### 4. 학습곡선 검토와50epoch의 의미

선택된 M1의 최고 epoch는23/26이고, 마지막 학습 loss는 약0.001이지만 검증 F1은66~67%대에서 정체했다. 검증 CE도 best 시점보다 마지막에 높아졌다. 현재 절차에서 M1은 학습 입력을 거의 맞히지만 검증 일반화가 그만큼 올라가지 않는 패턴이다. 단순 추가학습만으로 격차가 해결될 근거는 약하다.

M2의 최고 epoch는43/44다. 마지막 F1은 각 seed에서 best보다 약0.092/0.081%p 낮으며, 마지막5epoch는 약69.8% 부근이다. M3는36/40, 선택 KD의 M4/M5는46/40에서 best를 얻었다. 선택된 신경망10fit 중50epoch 마지막이 best인 실행은 없다. 따라서 **이번200개 개발조건에서50epoch를 대표 본실험의 공통 상한 후보로 유지할 근거는 있다.** 다만 cosine 학습률이 끝에서 작아지기 때문에 평탄해진 곡선만으로 전역 수렴을 증명하지 않는다.

낮은 M2 학습률1e−5 후보는 두 seed 모두50epoch가 best였지만 선택되지 않았다. “모든 후보가 충분히 수렴했다”고 말하지 않는다. 예산50/100/1000에서 동일한 수렴 양상을 확인한 것도 아니다. 현재 `epochs_frozen=false`는 유지했고, 곡선 검토 메모만 완료했다. **본실험용 동결파일·설정 확정은 다음 실행 단계이며, 이번 회수에서 본학습은 시작하지 않았다.**

학습 loss의 절대값을 M3와 M4/M5 사이에서 직접 비교하면 안 된다. M3는 CE이고 KD 모델은 가중 CE+T²KL이므로 숫자의 척도가 다르다. 비교 가능한 공통 검증 F1·정확도·GT CE를 사용한다. 아래 부록은 선택된10개 신경망 fit의 원본50epoch 중 일부를 발췌한 것이며, 전체 곡선은 JSON에 남아 있다.

### 5. 서비스별 결과가 말해주는 것

M2는 Instagram98.87%, TikTok99.25%, Spotify97.40% 수준의 클래스 F1을 보였지만, Google WWW44.05%, Fonts48.05%, Ads51.96%처럼 낮은 항목도 있었다. M5의 Google WWW는6.43%, YouTube는21.26%였다. 전체 평균만 보면 가려지는 서비스별 난이도 차이가 크다. Google 계열을 전부 못 맞힌다고도 말할 수 없다. M2의 Safebrowsing은81.19%이고 Gstatic은70.38%였다.

오류 예시로 M2는 두 seed 예측을 합친 Google IMASDK의400번 평가 중89번을 Ads로, Drive의400번 중68번을 Docs로 예측했다. 같은 검증4000개를 두 모델로 평가한 합계이므로8,000개의 독립 플로우 또는 각 서비스400개의 서로 다른 플로우라고 표현하지 않는다. Google WWW·YouTube 등의 학생 오류는 관측 패턴의 유사성뿐 아니라 학생 표현·학습 한계로도 설명될 수 있으며, 서비스 라벨 자체가 잘못됐다고 이 결과로 판정하지 않는다.

표의 클래스 F1은 각 seed의 클래스 F1을 먼저 계산한 뒤 평균한 값이다. 혼동행렬을 합쳐 새 F1을 계산한 값과 구분한다. 서비스별 precision/recall, 원본 혼동행렬과 예측확률은 검증 JSON/NPZ에서 추적할 수 있다.

### 6. 발표에서 가능한 문장과 피해야 할 문장

- 가능: “동일한 PPI 관측 구간·학습 표본·라벨 예산으로 M0~M5 개발 비교를 했고, 사전학습 교사의 개선이 작은 학생에게 충분히 이전되지 않는 양상을 확인했다.”
- 가능: “작은 학생은 약34배 작지만 이번 개발조건의 교사 성능과는 약25%p 차이가 있어, 성능을 유지하는 경량화 목표는 아직 입증하지 못했다.”
- 피함: “60회 반복으로 통계적으로 검증됐다.” 60은 탐색 후보 수이며 최종 설정의 개발 반복은2개다.
- 피함: “정제했으므로 누수·중복 문제가 완전히 없다.” 확인한 것은 정의한 PPI 키와 원본 ID 조건이며, 세션·공개 사전학습 원천 중복은 별도다.
- 피함: “사전학습이나 KD는 효과없다.” 현재 구조·라벨 예산·분할·후보 범위의 관찰이며 작은 양의 차이도 있다.
- 피함: “A100 학습이 빨랐으므로 실시간 CPU 배포 가능하다.” 학습 속도와 CPU 추론 및30패킷 관측 대기는 다르다.

### 7. 다음에 해야 할 것과 아직 측정하지 않은 것

다음 실행 전 선택 설정·공통 epoch를 동결하고, 사전 지정한 본 seed201~205의 대표200개 조건을 진행하는 것이 기존 계획의 다음 단계다. 그다음4월/5월 전체·학습 겹침·비겹침·공통 미관측을 분해하고 CPU 지연·처리량·메모리를 측정해야 한다. 현재 회수에서는 추가학습이나4/5월 점수 계산을 수행하지 않았다. 학생 구조 개선은 필요성이 제기됐지만, 원인을 가르는 별도 실험으로 설계해야 하며 유리한 설정만 몰래 바꿔 기존 비교에 섞지 않는다.

환경 `pip freeze`와 GPU 드라이버 전체 출력은 추가 회수했다. 여전히 실행별 독립 최고 VRAM, 정확한 개별 벽시계 시작/종료, 배치별 처리시간, 최종 CPU 벤치마크, 미사용 환경 외부 검증은 없다. 전체 환경 스냅샷을 이러한 미측정값의 대체물로 취급하지 않는다. 기계검증은 파일·실행계약의 일치 확인이고, 가설의 진실성이나 데이터셋 라벨 정확성을 증명하는 절차가 아니다.

### 부록 A. 선택한 신경망의 검증 F1 곡선 발췌(%)

|모델|seed|1epoch|5epoch|10epoch|20epoch|30epoch|40epoch|50epoch|
|---|---|---|---|---|---|---|---|---|
|M1|101|0.897|57.397|64.195|66.234|66.339|66.480|66.459|
|M1|102|2.713|53.767|62.699|65.965|67.471|67.649|67.430|
|M2|101|1.546|39.010|59.459|67.677|69.067|69.658|69.794|
|M2|102|3.519|40.702|60.408|67.187|68.525|69.660|69.821|
|M3|101|0.476|18.968|25.722|36.364|43.887|44.656|44.929|
|M3|102|1.447|17.237|27.217|34.958|40.758|43.296|43.270|
|M4|101|0.476|18.838|25.255|36.269|43.482|44.507|45.020|
|M4|102|1.499|17.675|26.463|35.216|41.062|43.560|43.334|
|M5|101|0.476|18.678|25.433|36.368|43.855|45.185|45.351|
|M5|102|1.593|16.985|27.507|35.705|41.040|43.499|43.354|

### 부록 B. 선택 설정의 서비스별 평균 F1(%)

|서비스|M0|M1|M2|M3|M4|M5|
|---|---|---|---|---|---|---|
|youtube|27.317|55.824|62.430|20.136|20.638|21.262|
|instagram|94.761|99.002|98.871|84.540|85.106|85.584|
|tiktok|98.477|99.010|99.249|80.231|80.793|82.554|
|snapchat|67.272|86.811|92.013|53.083|53.878|53.614|
|spotify|57.989|93.660|97.400|71.101|70.514|71.859|
|discord|83.895|98.489|96.848|81.889|81.114|80.856|
|google-www|19.436|36.882|44.048|7.930|8.197|6.430|
|google-play|36.429|59.677|63.859|45.023|43.733|43.273|
|google-services|47.471|67.863|67.755|31.378|32.316|32.514|
|google-gstatic|56.079|65.631|70.378|49.604|48.849|49.364|
|google-usercontent|40.325|73.862|69.919|43.704|43.548|44.356|
|google-authentication|39.339|64.480|66.791|43.478|43.659|42.108|
|google-fonts|32.504|43.327|48.050|29.357|27.380|27.347|
|google-drive|42.244|49.435|53.303|33.515|33.196|33.985|
|google-docs|45.522|61.378|63.726|37.070|39.152|38.455|
|google-translate|34.330|51.373|53.155|36.026|38.228|38.766|
|google-ads|26.427|44.863|51.962|20.398|21.039|21.541|
|google-safebrowsing|51.389|75.842|81.187|45.347|45.353|45.357|
|google-imasdk|32.284|48.080|50.745|26.558|27.124|28.453|
|google-calendar|47.249|71.990|66.198|43.666|45.195|43.979|

각 서비스의 두 seed 원본 support는 각각200개다. 원본 지표·예측과 연결된 파생 표이며 별도 재학습 결과가 아니다.

자동 점검 `a100`은 결과 회수·GPU 해제·분석 기록 완료 후 삭제했다. 추가 실험은 시작하지 않았다.

## 대표 본실험 결과 — Google 포함20·200개·5개 seed

개발 탐색과 별도로 seed201~205에서 M0~M5 **30fit**을 완료하고 로컬 검증했다. 신경망25fit은 각50epoch·1,600update, 트리5fit은 사전 지정한 조기종료 규칙을 사용했다. 개발 결과를 본실험의 반복에 재사용하지 않았다.

[학습 원본 ZIP — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts) · [학습 검증 원장](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/verified_training.json). 내부226파일. SHA256 `0a6ed0ab2a84e29c76734c5f09d377d6f7a9219c2b4d6ae0ecfd579ac22735be`.

고정 설정: M1 LR0.001 / M2 LR0.0001 / 학생 LR0.003 / LightGBM leaves31 / 공통KD α0.5·T1 /50epoch. 모든 checkpoint는2월 검증으로 선택하고 목록을 동결한 후4·5월에 평가했다. 원래 config와 데이터는 보존하고 별도 main_frozen.json을 실행기에 적용했다.

### 학습 완료와2월 checkpoint 선택

다음 점수는 본seed의 **2월 검증값**이며4월 성능과 구별한다. 시간은 모델 초기화·교사 예측·학습·검증·checkpoint 저장을 포함하고 ZIP 압축·전송을 제외한다.

|모델|2월 Macro-F1 평균±표본SD(%)|seed201~205 best epoch/round|5fit 시간 합(초)|
|---|---|---|---|
|M0|49.231 ± 0.746|138, 94, 102, 81, 180|35.0|
|M1|66.841 ± 1.019|20, 49, 24, 20, 33|210.6|
|M2|70.465 ± 0.907|43, 37, 40, 35, 46|199.0|
|M3|44.741 ± 0.965|40, 46, 46, 39, 47|34.1|
|M4|44.853 ± 0.979|40, 44, 40, 39, 37|38.2|
|M5|44.984 ± 0.881|44, 46, 45, 39, 45|38.2|

### 4·5월 시간차 평가

60건의 월×모델×seed 평가를 회수하여 모든 예측 ID·checkpoint 해시·부분집합 지표를 대조했다. [평가 원본 ZIP — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts) · [평가 검증 원장·전체 클래스 지표](../../experiments/2026-10-30_midterm_restart/main_recovered/evaluation_083e2ab53fa66d6f/verified_evaluation.json). SHA256 `083e2ab53fa66d6fcb414e42e5205211aebb8378e182cbbce37b60b1a1fd51b1`.

주 결과는4월 All, 시간 변화 평가는5월 All이다. ±는5개 seed의 **표본 표준편차(ddof=1)**이며 신뢰구간이 아니다. 같은 월의 동일 평가자료를 반복 평가하므로5개 반복을 독립 수집 데이터셋5개로 보지 않는다. 학습 겹침은 각 seed의 실제200개 학습표본 기준이고 Common-unseen은 사전 등록된 학습·개발·검증 목록의 합집합과 겹치지 않는 부분집합이다.

#### 202504 전체·겹침·비겹침·공통 미관측

|부분집합|모델|seed별 N 범위|정답 support>0 클래스 수|Macro-F1 평균±SD(%)|Accuracy 평균±SD(%)|
|---|---|---|---|---|---|
|all|M0|379,194–379,194|20–20|34.075 ± 0.379|47.078 ± 0.493|
|all|M1|379,194–379,194|20–20|50.332 ± 1.617|65.000 ± 1.685|
|all|M2|379,194–379,194|20–20|53.771 ± 1.743|69.563 ± 1.304|
|all|M3|379,194–379,194|20–20|32.493 ± 0.982|45.536 ± 0.920|
|all|M4|379,194–379,194|20–20|32.451 ± 0.736|45.347 ± 0.949|
|all|M5|379,194–379,194|20–20|32.743 ± 0.815|45.935 ± 0.689|
|train_overlap|M0|0–7|0–4|N/A|N/A|
|train_overlap|M1|0–7|0–4|N/A|N/A|
|train_overlap|M2|0–7|0–4|N/A|N/A|
|train_overlap|M3|0–7|0–4|N/A|N/A|
|train_overlap|M4|0–7|0–4|N/A|N/A|
|train_overlap|M5|0–7|0–4|N/A|N/A|
|train_nonoverlap|M0|379,187–379,194|20–20|34.075 ± 0.380|47.078 ± 0.493|
|train_nonoverlap|M1|379,187–379,194|20–20|50.332 ± 1.617|65.000 ± 1.685|
|train_nonoverlap|M2|379,187–379,194|20–20|53.771 ± 1.743|69.564 ± 1.305|
|train_nonoverlap|M3|379,187–379,194|20–20|32.493 ± 0.982|45.536 ± 0.920|
|train_nonoverlap|M4|379,187–379,194|20–20|32.451 ± 0.736|45.348 ± 0.949|
|train_nonoverlap|M5|379,187–379,194|20–20|32.743 ± 0.815|45.936 ± 0.690|
|common_unseen|M0|376,465–376,465|20–20|34.215 ± 0.414|47.373 ± 0.496|
|common_unseen|M1|376,465–376,465|20–20|50.575 ± 1.678|65.335 ± 1.777|
|common_unseen|M2|376,465–376,465|20–20|54.020 ± 1.634|69.968 ± 1.287|
|common_unseen|M3|376,465–376,465|20–20|32.702 ± 0.942|45.767 ± 0.920|
|common_unseen|M4|376,465–376,465|20–20|32.698 ± 0.717|45.666 ± 0.952|
|common_unseen|M5|376,465–376,465|20–20|32.955 ± 0.700|46.191 ± 0.640|

고정20클래스 Macro-F1이며 해당 부분집합에서 정답·예측 모두 없는 클래스의F1은0이다. 빈 집합은N/A다. 부분집합마다 클래스 구성·난이도가 달라 단순 점수 차이를 누수의 인과효과로 단정하지 않는다.

<details><summary>학습 겹침 부분집합 — seed별 원점수</summary>

4월 seed203은 겹침 표본이0개이므로5seed 평균은N/A로 표시한다. 다른 반복의 비어 있지 않은 결과는 아래에 그대로 남긴다. 두 월 모두 겹침 표본이 극히 적어 안정적인 성능 추정으로 해석하지 않는다.

|seed|모델|N|support>0 클래스|Macro-F1(%)|Accuracy(%)|
|---|---|---|---|---|---|
|201|M0|5|4|13.333|60.000|
|201|M1|5|4|13.333|60.000|
|201|M2|5|4|13.333|60.000|
|201|M3|5|4|13.333|60.000|
|201|M4|5|4|13.333|60.000|
|201|M5|5|4|10.000|40.000|
|202|M0|1|1|5.000|100.000|
|202|M1|1|1|5.000|100.000|
|202|M2|1|1|5.000|100.000|
|202|M3|1|1|5.000|100.000|
|202|M4|1|1|5.000|100.000|
|202|M5|1|1|5.000|100.000|
|203|M0|0|0|N/A|N/A|
|203|M1|0|0|N/A|N/A|
|203|M2|0|0|N/A|N/A|
|203|M3|0|0|N/A|N/A|
|203|M4|0|0|N/A|N/A|
|203|M5|0|0|N/A|N/A|
|204|M0|5|3|10.000|60.000|
|204|M1|5|3|10.000|60.000|
|204|M2|5|3|10.000|60.000|
|204|M3|5|3|0.000|0.000|
|204|M4|5|3|0.000|0.000|
|204|M5|5|3|0.000|0.000|
|205|M0|7|3|10.000|42.857|
|205|M1|7|3|10.000|42.857|
|205|M2|7|3|10.000|42.857|
|205|M3|7|3|5.000|14.286|
|205|M4|7|3|0.000|0.000|
|205|M5|7|3|5.000|14.286|


</details>
#### 202505 전체·겹침·비겹침·공통 미관측

|부분집합|모델|seed별 N 범위|정답 support>0 클래스 수|Macro-F1 평균±SD(%)|Accuracy 평균±SD(%)|
|---|---|---|---|---|---|
|all|M0|365,258–365,258|20–20|34.248 ± 0.423|46.162 ± 0.516|
|all|M1|365,258–365,258|20–20|50.148 ± 1.661|64.412 ± 1.689|
|all|M2|365,258–365,258|20–20|53.680 ± 1.456|69.013 ± 1.099|
|all|M3|365,258–365,258|20–20|32.777 ± 0.975|44.757 ± 1.031|
|all|M4|365,258–365,258|20–20|32.716 ± 0.697|44.560 ± 1.074|
|all|M5|365,258–365,258|20–20|32.990 ± 0.805|45.149 ± 0.736|
|train_overlap|M0|2–6|1–4|4.000 ± 4.183|35.000 ± 41.833|
|train_overlap|M1|2–6|1–4|4.000 ± 4.183|35.000 ± 41.833|
|train_overlap|M2|2–6|1–4|4.000 ± 4.183|35.000 ± 41.833|
|train_overlap|M3|2–6|1–4|3.000 ± 4.472|30.000 ± 44.721|
|train_overlap|M4|2–6|1–4|3.000 ± 4.472|30.000 ± 44.721|
|train_overlap|M5|2–6|1–4|3.000 ± 4.472|30.000 ± 44.721|
|train_nonoverlap|M0|365,252–365,256|20–20|34.248 ± 0.422|46.162 ± 0.516|
|train_nonoverlap|M1|365,252–365,256|20–20|50.148 ± 1.661|64.413 ± 1.689|
|train_nonoverlap|M2|365,252–365,256|20–20|53.681 ± 1.456|69.013 ± 1.099|
|train_nonoverlap|M3|365,252–365,256|20–20|32.777 ± 0.975|44.757 ± 1.031|
|train_nonoverlap|M4|365,252–365,256|20–20|32.716 ± 0.698|44.560 ± 1.074|
|train_nonoverlap|M5|365,252–365,256|20–20|32.990 ± 0.805|45.149 ± 0.737|
|common_unseen|M0|362,640–362,640|20–20|34.377 ± 0.447|46.420 ± 0.515|
|common_unseen|M1|362,640–362,640|20–20|50.381 ± 1.717|64.724 ± 1.777|
|common_unseen|M2|362,640–362,640|20–20|53.909 ± 1.382|69.392 ± 1.103|
|common_unseen|M3|362,640–362,640|20–20|32.983 ± 0.939|44.976 ± 1.025|
|common_unseen|M4|362,640–362,640|20–20|32.964 ± 0.688|44.873 ± 1.079|
|common_unseen|M5|362,640–362,640|20–20|33.205 ± 0.704|45.398 ± 0.685|

고정20클래스 Macro-F1이며 해당 부분집합에서 정답·예측 모두 없는 클래스의F1은0이다. 빈 집합은N/A다. 부분집합마다 클래스 구성·난이도가 달라 단순 점수 차이를 누수의 인과효과로 단정하지 않는다.

<details><summary>학습 겹침 부분집합 — seed별 원점수</summary>

4월 seed203은 겹침 표본이0개이므로5seed 평균은N/A로 표시한다. 다른 반복의 비어 있지 않은 결과는 아래에 그대로 남긴다. 두 월 모두 겹침 표본이 극히 적어 안정적인 성능 추정으로 해석하지 않는다.

|seed|모델|N|support>0 클래스|Macro-F1(%)|Accuracy(%)|
|---|---|---|---|---|---|
|201|M0|3|2|10.000|100.000|
|201|M1|3|2|10.000|100.000|
|201|M2|3|2|10.000|100.000|
|201|M3|3|2|10.000|100.000|
|201|M4|3|2|10.000|100.000|
|201|M5|3|2|10.000|100.000|
|202|M0|2|1|0.000|0.000|
|202|M1|2|1|0.000|0.000|
|202|M2|2|1|0.000|0.000|
|202|M3|2|1|0.000|0.000|
|202|M4|2|1|0.000|0.000|
|202|M5|2|1|0.000|0.000|
|203|M0|4|2|5.000|50.000|
|203|M1|4|2|5.000|50.000|
|203|M2|4|2|5.000|50.000|
|203|M3|4|2|5.000|50.000|
|203|M4|4|2|5.000|50.000|
|203|M5|4|2|5.000|50.000|
|204|M0|4|4|5.000|25.000|
|204|M1|4|4|5.000|25.000|
|204|M2|4|4|5.000|25.000|
|204|M3|4|4|0.000|0.000|
|204|M4|4|4|0.000|0.000|
|204|M5|4|4|0.000|0.000|
|205|M0|6|2|0.000|0.000|
|205|M1|6|2|0.000|0.000|
|205|M2|6|2|0.000|0.000|
|205|M3|6|2|0.000|0.000|
|205|M4|6|2|0.000|0.000|
|205|M5|6|2|0.000|0.000|


</details>
### 같은 seed로 짝지은 핵심 비교

각 숫자는 F1의 절대 **%p 차이**다. seed별 차이를 모두 보이며, 별도 유의성 검정은 수행하지 않았다.

|월|차이|201|202|203|204|205|평균±SD(%p)|
|---|---|---|---|---|---|---|---|
|202504|M2−M1|+4.731|+4.775|+4.446|-1.482|+4.728|3.439 ± 2.754|
|202504|M4−M3|-0.412|-0.063|+0.545|+0.118|-0.398|-0.042 ± 0.398|
|202504|M5−M3|-0.593|+0.378|+0.333|+0.739|+0.394|0.250 ± 0.499|
|202504|M5−M4|-0.181|+0.441|-0.212|+0.621|+0.792|0.292 ± 0.463|
|202504|M2−M5|+20.176|+20.804|+22.989|+17.783|+23.390|21.028 ± 2.276|
|202505|M2−M1|+5.096|+4.853|+4.142|-1.071|+4.641|3.532 ± 2.597|
|202505|M4−M3|-0.471|-0.082|+0.530|+0.143|-0.427|-0.062 ± 0.417|
|202505|M5−M3|-0.658|+0.361|+0.366|+0.730|+0.264|0.213 ± 0.518|
|202505|M5−M4|-0.186|+0.443|-0.163|+0.587|+0.692|0.274 ± 0.420|
|202505|M2−M5|+20.207|+20.402|+22.169|+17.915|+22.758|20.690 ± 1.903|

성능 목표(M2 대비 M5 감소2%p 이내):4월 평균 감소 **21.028%p**, 개별 반복에서2%p 이내는 **0/5**다. 평균 기준 판정과 반복별 안정성을 분리한다. 파라미터는695,593→20,180으로약34.47배 감소했다.

<details><summary>202504 서비스별 All 평균F1·support</summary>


|서비스|월별 평가 행 수|M0|M1|M2|M3|M4|M5|
|---|---|---|---|---|---|---|---|
|youtube|60171|27.544|64.487|68.214|35.385|35.905|36.554|
|instagram|53247|97.752|98.887|99.718|93.235|92.773|93.198|
|tiktok|11933|91.676|96.168|95.738|65.408|63.894|65.105|
|snapchat|57813|77.861|90.136|93.154|65.820|65.321|66.261|
|spotify|17181|51.129|83.913|89.623|56.957|57.551|57.175|
|discord|5770|63.189|94.172|73.805|62.439|62.707|62.259|
|google-www|22292|19.533|39.439|47.688|6.088|6.925|6.568|
|google-play|12556|21.016|43.792|54.536|31.293|30.364|31.076|
|google-services|16790|36.781|50.137|60.743|23.876|24.926|24.805|
|google-gstatic|16310|41.699|49.413|54.283|44.613|44.303|44.608|
|google-usercontent|19125|24.146|55.605|58.688|37.448|37.049|36.436|
|google-authentication|7616|14.311|41.301|45.435|24.087|24.051|24.611|
|google-fonts|7884|22.563|23.336|26.278|17.885|18.302|18.225|
|google-drive|511|3.473|6.189|8.089|4.629|4.110|4.620|
|google-docs|973|6.313|15.565|19.298|8.237|7.670|8.618|
|google-translate|518|1.614|5.173|5.232|4.105|3.901|3.844|
|google-ads|41712|32.399|41.428|47.602|18.671|18.097|19.176|
|google-safebrowsing|1657|13.867|40.660|48.203|8.531|8.855|8.825|
|google-imasdk|551|2.479|3.543|5.988|1.623|1.551|1.524|
|google-calendar|24584|32.162|63.293|73.112|39.525|40.759|41.373|


</details>
<details><summary>202505 서비스별 All 평균F1·support</summary>


|서비스|월별 평가 행 수|M0|M1|M2|M3|M4|M5|
|---|---|---|---|---|---|---|---|
|youtube|61631|27.422|64.731|68.371|36.083|36.669|37.397|
|instagram|45256|97.346|98.801|99.587|91.639|90.942|91.333|
|tiktok|13193|96.440|96.779|97.201|70.337|69.226|70.043|
|snapchat|53748|78.036|90.328|93.305|66.722|66.285|67.168|
|spotify|16916|51.492|84.354|89.969|58.066|58.784|58.355|
|discord|6035|65.547|94.774|75.968|65.446|65.537|64.788|
|google-www|22661|20.143|40.171|47.797|6.563|7.503|7.198|
|google-play|12307|20.580|41.910|52.092|29.723|28.682|29.475|
|google-services|16838|37.086|50.010|61.038|24.773|25.641|25.756|
|google-gstatic|15724|42.123|48.590|54.539|43.338|42.940|43.255|
|google-usercontent|18222|23.343|54.783|58.817|36.172|35.870|35.336|
|google-authentication|6976|13.029|41.217|43.949|24.100|23.858|24.647|
|google-fonts|7762|21.998|23.272|26.401|17.978|18.100|18.010|
|google-drive|504|3.351|5.647|7.591|4.145|3.770|4.217|
|google-docs|879|6.157|14.775|19.427|7.064|6.701|7.383|
|google-translate|466|1.577|4.489|4.761|4.289|3.982|3.869|
|google-ads|39760|32.027|40.815|46.288|18.921|18.267|19.357|
|google-safebrowsing|1587|12.838|39.155|46.695|8.707|9.031|9.018|
|google-imasdk|640|2.626|3.950|6.034|1.794|1.716|1.652|
|google-calendar|24153|31.803|64.411|73.777|39.684|40.810|41.545|


</details>
지표 재계산에 필요한 행ID·정답·예측라벨·정답 log확률·최대확률을 보존했다. 전송량 절약을 위해 전체20차원 확률벡터는 보존하지 않았으며, 체크포인트와 입력에서 재생성할 수 있다. 원본 예측·전체 혼동행렬·precision/recall·고정 클래스 순서는 평가 원장에 연결돼 있다.

### 로컬 CPU 비용 측정

모델마다 독립된 새 프로세스를 사용했다. CPU1스레드·FP32,20서비스에서6~7개씩 선정한 공통128입력, batch1 warm-up100회 후1,000회, batch128 warm-up10회 후100회를 측정했다. batch1은128입력을 순환한다. 모델별 표는5개 실행의 중앙값/개별p95/처리량을 각각 평균한 값이다. p95의 평균은 전체 측정값을 합친 하나의p95가 아니다.


|모델|batch1 중앙값 평균±SD(ms)|개별p95 평균±SD(ms)|128묶음 flows/s 평균±SD|추론가중치파일MiB 평균±SD|warm RSS MiB 평균±SD|독립process peak MiB 평균±SD|
|---|---|---|---|---|---|---|
|M0|0.310 ± 0.068|0.386 ± 0.103|7571.075 ± 2588.734|7.229 ± 2.479|297.031 ± 4.333|297.372 ± 4.315|
|M1|0.350 ± 0.003|0.417 ± 0.030|97.599 ± 4.573|2.724 ± 0.000|275.991 ± 0.548|477.356 ± 24.732|
|M2|0.353 ± 0.006|0.571 ± 0.231|98.786 ± 5.504|2.724 ± 0.000|276.191 ± 0.139|489.238 ± 1.336|
|M3|0.040 ± 0.001|0.058 ± 0.028|6986.028 ± 276.718|0.080 ± 0.000|263.406 ± 0.312|275.962 ± 1.154|
|M4|0.040 ± 0.000|0.049 ± 0.005|7100.589 ± 260.879|0.080 ± 0.000|263.344 ± 0.163|275.250 ± 1.006|
|M5|0.040 ± 0.000|0.065 ± 0.038|7035.760 ± 256.572|0.080 ± 0.000|263.584 ± 0.232|275.834 ± 1.384|

NN은 내부 고정변환·embedding을 포함한 logits forward, M0는16통계 추출과 확률 예측을 포함한 시간을 주 수치로 사용했다. 파일 로딩·canonicalization·numpy→tensor 준비·패킷 관측 대기는 제외한다. 실시간 네트워크 end-to-end 지연이 아니다. RSS/peak는 라이브러리·할당자·입력 등을 포함한 프로세스 수치로 모델 고유 메모리와 같지 않다. M0의 통계 추출/forward 분해, raw1,000회 지연, baseline/loaded/warm RSS는 원본에 보존했다.

측정 환경: `{"platform": "macOS-27.0.1-arm64-arm-64bit", "machine": "arm64", "python": "3.12.14", "cpu": "Apple M5", "packages": {"torch": "2.14.0", "numpy": "2.5.3", "cesnet-models": "0.4.1", "lightgbm": "4.6.0"}}`.

[CPU 측정 원본 폴더](../../experiments/2026-10-30_midterm_restart/main_cpu_benchmark) 및 실행 코드 main_cpu_benchmark.py에 측정 범위와 반복을 기록했다.

### 해석 범위와 다음 단계

대표 조건의 완료 여부는 학습30·월별60·CPU30을 각각 구분한다. 50/100/1000개 라벨 예산, non-Google13/Google-only20, FLOWSTATS, 학생 구조 변경, 실시간 수집 시연은 이 실행에 포함하지 않았다. 4·5월은 과거 연구에서 이미 본 월이므로 완전히 미사용 외부 최종 테스트라고 부르지 않는다. 현재 고정 설계에서는 시간차 평가로 사용했고 그 점수로 설정을 다시 선택하지 않았다.

### 이번 본실험을 처음 보는 사람을 위한 해석

**이번 단계는 계획한 대표 조건을 끝까지 실행한 것이며, 목표 성능을 달성한 것과는 다르다.** 데이터와 모델 구조를 다시 정리한 뒤, Google 포함20서비스·클래스당200개 정답·최대30패킷의 크기/방향/IPT만으로 비교했다. 개발용 seed101/102에서 설정을 선택한 뒤 이를 고정하고, 새로운 seed201~205에서 여섯 모델을 각각 학습했다. 실제 학습 입력은 한 반복당4,000개이며 M0~M5에 동일한 입력을 제공했다. M4/M5에도 추가 입력은 주지 않았다. 교사 확률은 입력 특징이 아니라 학습 손실에 사용하는 신호다. 추론 시 학생만 실행한다.

| 모델 | 이번 실험에서 맡은 역할 | 4월 Macro-F1 평균±SD(%) | 5월 Macro-F1 평균±SD(%) |
|---|---|---|---|
| M0 | 첫30패킷에서 계산한16통계 + LightGBM | 34.075 ± 0.379 | 34.248 ± 0.423 |
| M1 | 큰 교사 구조를 공개 학습 가중치 없이 직접 학습 | 50.332 ± 1.617 | 50.148 ± 1.661 |
| M2 | 같은 큰 구조에 공개 사전학습 가중치를 사용해 전체 미세조정 | **53.771 ± 1.743** | **53.680 ± 1.456** |
| M3 | 작은 학생을 정답만으로 직접 학습 | 32.493 ± 0.982 | 32.777 ± 0.975 |
| M4 | 작은 학생에 M1의 확률을 증류 | 32.451 ± 0.736 | 32.716 ± 0.697 |
| M5 | 작은 학생에 M2의 확률을 증류 | 32.743 ± 0.815 | 32.990 ± 0.805 |

**첫째, 사전학습을 활용한 교사는 평균적으로 더 좋았지만 모든 반복·서비스에서 이긴 것은 아니다.** M2−M1은4월 +3.439%p,5월 +3.532%p였다. 두 월 모두5개 seed 중4개에서 M2가 더 좋고 seed204에서는 M1이 더 좋았다. M1/M2는 구조와 목표 데이터는 같지만 BN 통계 처리·학습률·GeM 초기값을 포함한 적응 절차도 다르다. 따라서 이는 정해진 두 학습 절차의 비교이며, 사전학습 초기값만의 순수 효과를 분리한 실험은 아니다.

**둘째, 이번의 단순한 작은 학생에서는 증류 효과가 작았다.** M5−M3은4월 평균 +0.250%p,5월 +0.213%p다. 둘 다4/5반복에서 양수였지만 seed201에서는 각각 −0.593/−0.658%p였다. M4−M3 평균은4월 −0.042%p,5월 −0.062%p로 거의 같거나 약간 낮았다. M5−M4 역시 +0.292/+0.274%p에 그쳤고5반복 중3개에서만 양수였다. 별도 유의성 검정을 하지 않았으며 ‘더 좋은 교사를 쓰면 학생도 큰 폭으로 좋아진다’는 주장은 이 결과로 지지되지 않는다. 이 결론은 현재 구조·데이터·선택한 KD 설정에 한정되며 모든 증류 방법의 불가능성을 뜻하지 않는다.

**셋째, 파라미터 축소는 달성했지만 교사를 대체할 성능은 확보하지 못했다.** 교사695,593개에서 학생20,180개로 약34.47배 작아졌다. 그러나 주 평가인4월에서 M2−M5는21.028%p이며 다섯 반복 모두2%p 목표를 넘었다(최소17.783, 최대23.390%p). 5월도20.690%p 차이다. 따라서 ‘크기를 줄이면서 교사와 비슷한 성능을 유지했다’고 발표하면 안 된다. 학생은 이번 조건에서 M0보다도 평균 F1이 약1.3%p 낮았다. 크기와 정확도 사이의 현재 한계를 확인한 결과다.

**넷째, Google 서비스의 어려움은 정밀도와 재현율을 나눠 봐야 한다.** 4월 M2에서 Instagram F1은99.718%, Snapchat93.154%인 반면 Google Drive8.089%, Translate5.232%, IMASDK5.988%였다. 예를 들어 Drive는 재현율39.256%인데 정밀도가4.524%라서 F1이 낮았다. 실제 Drive를 일부 맞히더라도 다른 서비스를 Drive라고 예측하는 오탐이 많다는 뜻이다. M5의 Google WWW는 재현율4.572%, F1 6.568%여서 해당 서비스를 놓치는 문제도 컸다. M2의 Discord는 재현율99.445%지만 정밀도59.687%였고, 직접학습 교사 M1의 Discord F1 94.172%보다 낮은73.805%였다. 사전학습의 평균 이득이 서비스별 이득을 보장하지 않는 예다. 모든 서비스별 precision·recall·F1과 혼동행렬은 원본 원장에 보존했다.

다만 이 혼합20 실험만으로 ‘Google 계열이어서 어려워졌다’는 인과관계를 확정할 수는 없다. 서비스 간 비슷한 PPI, 짧은 플로우, 자연 분포의 클래스 불균형, 표현력·최적화 차이 등이 함께 영향을 줄 수 있다. 각 원인의 비중은 후속 통제 실험에서 분리해야 한다.

**다섯째, 낮은 점수를 학습·평가 간 완전 동일 입력의 중복 탓으로 설명하기는 어렵다.** 각 seed의 실제 학습4,000개와 정확히 같은 canonical30패킷 PPI는4월0~7개,5월2~6개뿐이었다. 두 월 모두 전체 평가의0.002% 미만이다. 해당 입력을 제외한 결과는 전체 결과와 거의 같다. 개발·검증·최대 라벨 예산 목록까지 함께 제외한 공통 미관측 부분집합에서도 M2/M5의 큰 차이가 남았다(4월54.020% 대32.955%). 이는 이번 정의의 ‘완전히 동일한 입력’ 중복에 대한 확인이다. 비슷하지만 동일하지 않은 플로우, 같은 사용자·연결에서 파생된 상관관계, 교사 bin화 이후 같은 표현이 되는 경우까지 없음을 입증한 것은 아니다. 겹침 집합 자체는 표본이 너무 적어 별도의 안정적인 성능 비교로 해석하지 않는다.

**여섯째, 2월 검증 점수와4월 평가 점수의 차이를 전부 시간 변화로 설명하면 안 된다.** M2는2월70.465%,4월53.771%이고 M5는44.984%에서32.743%로 달라졌다. 하지만2월은클래스당200개인 균형 검증셋이고4월은 자연 분포379,194개다. Macro-F1도 각 서비스의 정밀도에 영향을 받으므로 클래스 비율 변화의 영향에서 완전히 자유롭지 않다. 시간 변화, 표본 구성, 검증 선택 효과가 섞여 있으며 이 실험에서 각각의 영향을 분리하지 않았다. 4월과5월은 자연 분포 평가에서 비슷한 순위·성능을 보였지만 두 달만으로 장기 안정성을 보장하지 않는다.

**CPU에서는 학생이 빠르지만 측정 조건을 붙여 말해야 한다.** Apple M5의 CPU1스레드·FP32에서 batch1 중앙값의5반복 평균은 M2 약0.353ms, M5 약0.040ms로약8.86배 차이였다. 이는 준비된 PPI를 모델에 넣는 실행 구간이며 패킷 수집 대기나 전체 서비스 응답 시간이 아니다. M5의 warm RSS는약263.6MiB, M2는276.2MiB로, 파라미터가34.47배 줄었다고 프로세스 메모리도34.47배 줄지는 않았다. Python·Torch·할당자 등이 포함되기 때문이다.

교사의 batch128 처리량은 약99flow/s로 batch1 시간에서 단순 예상할 수 있는 값보다 낮게 측정됐다. 이 현상은5개 반복에서 나타났지만 원인은 분석하지 않았다. 로컬 CPU 백엔드·연산/배치 크기 특성에 민감할 수 있으므로 이를 교사 모델의 보편적인 처리량 한계로 일반화하지 않는다. 같은 조건의 학생 처리량은약7,036flow/s였으며, 실제 배포를 결정할 때에는 목표 장비·배치 크기에서 별도 확인해야 한다. 측정 중 호스트의 다른 작업이 완전히 없었다고 통제하지 않았고, 실행 순서는 seed마다 M0→M5로 고정되어 있었다. 원본 지연30,000개와 batch128 측정3,000개, 측정 코드·파일 해시를 보존했다.

### 발표에서 사용할 결론과 다음 작업

발표의 중심 문장은 **“통제를 갖춘 대표 조건에서 사전학습 교사의 평균 이득은 관찰했지만, 현재20K 학생의 단순 logit 증류로는 큰 교사의 성능을 보존하지 못했다. 다음 단계는 라벨 수와 학생 표현 구조 중 무엇이 병목인지 구분하는 것이다.”**가 적절하다. 목표 미달을 숨기는 대신 동일 입력·반복·선택 기준·원본 결과로 이를 설명할 수 있게 된 것이 이번 단계의 성과다.

예정된 다음 순서는 고정된 설정으로50/100/1000개 라벨 곡선을 만들고, 준비된 다른 서비스 구성과 비교하는 것이다. 이것은 아직 실행하지 않았다. 라벨을 늘렸을 때 M3/M5가 얼마나 개선되고 교사와의 차이가 줄어드는지 봐야 데이터 부족과 현재 학생 구조의 한계를 구별할 근거가 늘어난다. 그래도 차이가 크다면 승인된 후보B(잔차/팽창 합성곱 등)와 같은 학생 표현 개선을 별도 개발 실험으로 검토할 수 있다. 이번4·5월 점수에 맞춰 현재 설정을 조용히 바꾸거나 같은 결과를 다시 ‘미사용 최종 테스트’로 부르면 안 된다. FLOWSTATS와 다른 공개 모델 비교는 중간발표 이후의 별도 입력·구조 실험이다.

### 실행 종료와 원본 보존

학습·평가 계산은23:32:07 KST 시작 후2,151.786초(35분51.8초)에 완료됐다. 모든 결과 회수·검증 후2026-10-31 00:17:21 KST에 A100 비연결 UI를 확인했다. 실행45분 상한 안에 계산은 끝났고, 결과 보존과 종료 확인까지 포함한 시간은약45분14초였다. 이는 과금 명세에서 측정한 정확한 비용이나 세션 연결 전체 시간은 아니다.

학습 원본 ZIP 약217MB, 평가 원본 ZIP 약220MB, 최종 로그·런타임 메타데이터를 각각 보존했다. 전체 SHA256·ZIP CRC·내부 파일 해시를 대조했으며 학습30개와 평가60개의 입력ID, 체크포인트 연결, 선택 규칙, 지표를 검증했다. 환경별 버전·pip freeze·nvidia-smi·GPU 학습 메모리·CPU 측정 원본도 연결한다. 압축·전송 시간은 순수 학습 시간과 구분한다. GPU 학습 peak allocation은 교사약915.5MiB, 직접학습 학생78.2MiB, KD학생173.1MiB였으며 CPU 추론 RSS와 같은 지표가 아니다.

이번 실행은 대표 조건만 완료했다. 라벨 예산·서비스 구성 전체 실험, 이상 탐지·미등록 서비스 판별, 실시간 수집·배포 시연, 새로운 외부 미사용 데이터 검증까지 완료한 것으로 확대해서 설명하지 않는다.

## 후속 본실험 실행 기록 — 라벨 수와 서비스 구성 확장

이 절은 대표200개 조건의 완료 결과와 구분한 후속 캠페인이다. **2026-10-31 사용자가 남은 작업의 계속 진행을 승인했다. 새로 계획한 학습은150fit이며, 원격 진행 수와 로컬 회수·검증 수를 구분한다.** 회수 전 로그는 성능 결과표에 편입하지 않는다. 대표200개 조건30fit은 재학습하지 않고 기존 검증 결과를 재사용한다.

### 검증하려는 질문과 실행 범위

|단계|서비스 구성|클래스당 학습 수|한 fit의 학습 행|M0~M5 × 본 seed5개|신경망50epoch 총update|
|---|---|---:|---:|---:|---:|
|mixed_n50|Google 포함20|50|1,000|30fit|400|
|mixed_n100|Google 포함20|100|2,000|30fit|800|
|mixed_n1000|Google 포함20|1,000|20,000|30fit|7,850|
|nongoogle_n200|비Google13|200|2,600|30fit|1,050|
|googleonly_n200|Google 계열20|200|4,000|30fit|1,600|

첫 세 단계는 기존200개 결과와 연결해 **50→100→200→1000개에서 각 모델이 얼마나 개선되는가**, 사전학습과KD의 효과가 라벨 수에 따라 어떻게 변하는가를 본다. 뒤 두 단계는 **어떤 서비스 구성에서 성능과 증류 효과가 달라지는가**를 확인한다. 정제 후 사전 합의한 최소 고유 표본 기준을 통과한 실제 구성은 비Google13·Google계열20이다. 이름을20/24개라고 부풀리지 않는다.

클래스 수와 서비스 목록이 다르므로 세 구성의 평균F1 차이를 Google 포함 여부만의 인과 효과라고 해석할 수 없다. 구성별M2−M1, M5−M3, M5−M4 등의 대응 차이를 함께 비교해야 한다. 이번 캠페인에 다른 두 구성의50/100/1000개 조합까지 추가하지 않았다.

### 고정한 사항과 공정성의 범위

- 입력은 첫 최대30패킷의IPT·방향·크기다. 짧은 플로우와 고정 변환, PPI중복 정제·원본ID 분할·마스크 규칙은 기존 준비본을 그대로 사용한다. FLOWSTATS나새채널은 추가하지 않는다.
- M1/M2/학생 학습률은각각0.001/0.0001/0.003, 공통KD는α0.5·T1, 배치128, FP32, 본seed201~205다. 4·5월 점수를 보고 다시 탐색하지 않는다.
- 신경망은 공통50epoch다. 표본 수가 많을수록1epoch의배치 수가 많으므로 **동일epoch는동일update·동일계산량 비교가 아니다.** 이 학습량 차이를 숨기지 않는다. M0는50epoch신경망규칙이 아닌 기존LightGBM 최대500round·검증조기종료 규칙을 사용한다.
- 각seed의표본목록은최대1000개목록의동일한중첩부분집합이며, 모든모델이같은표본을사용한다. 각fit의원본ID·입력·라벨해시를보존한다.
- 모델의공통body는동일하고출력head만실제클래스수에맞춘다. 교사는`686613+449×C`, 학생은`18880+65×C`파라미터다. 20클래스에서는695,593/20,180개,13클래스에서는692,450/19,725개다.
- checkpoint선택은2월검증만사용한다. 검증행수는포함20의4,000개,비Google13의2,600개,Google계열20의3,933개다. 마지막구성까지모두클래스당200개라고표현하지않는다.

[동결된후속계획](../../experiments/2026-10-30_midterm_restart/continuation_frozen.json)의SHA256은`ace1bbf4e9465ff9febc3eab3d7051a7b23484683a7db160577d233ee8f65d53`이다. 기존config/data/models/training/대표실행기원본해시를검증하며공유학습코드를수정하지않았다. [사전점검 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)은표본균형·중첩·검증ID분리와M0평가방식일치를확인했으며성능결과가아니다.

### 실행 환경과 평가 분담

A10040GB에서신경망학습125fit과4·5월신경망평가250건을수행한다. 트리학습25fit은기존설계대로CPU1스레드다. 트리의월별평가50건은회수한동일checkpoint로로컬CPU1에서수행해A100대기비용을줄인다. 전체평가는원격250+로컬50=300건이다. 평가월·원본ID·특징변환·배치1024·지표·부분집합정의는동일하다.

M0평가경로를옮기기사전점검에서기존검증4,000개의예측라벨이완전히일치했고확률최대절대차이는1.11×10⁻¹⁶이었다. 4월앞4,096개의예측라벨과float32정답로그확률도일치했다. 플랫폼간모든확률이비트단위로동일하다는보장은아니다. 16개PPI통계는입력행마다독립적으로계산하며월·구성별로재사용한다.

전체·학습입력겹침·비겹침·공통미관측을분리하여각서비스support,precision,recall,F1과혼동행렬을보존한다. 작은겹침집단의불안정한Macro-F1을전체20서비스성능처럼해석하지않는다. 모델별CPU지연·메모리는기존대표조건측정과새조건측정을구분한다. **이번후속조건의CPU비용측정,발표슬라이드·데모완료는아직선언하지않는다.**

### 실패도 남기는 운영 기록

초기큰업로드도중연결이끊겼으며, 분할전송후00:53:41KST에시작한PID2161도이후연결이끊겼다. PID2161은로그에서50개조건학습30회와월별평가1건까지확인했지만, 생성된200,170,527바이트학습ZIP을로컬에회수하기전에세션이사라졌다. 새연결에서는작업폴더가없고활성기존세션도없었다. **해당30회는사용가능한완료실험으로집계하지않는다.** 연결해제원인은확정하지못했으며, 메모리부족·유휴종료·할당량중어느것때문이라고단정하지않는다. [소실증거와마지막원격해시 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)를보존했다.

이후표준파일업로드로4ZIP·내부40파일을모두전송하고해시를확인했다. 다운로드버튼은로컬파일을생성하지못해,화면textarea의base64를131,072문자씩읽는대체회수경로를검증했다. 전체텍스트를한번에읽으면200,000문자부근에서잘리므로원본길이·조각SHA·전체SHA를반드시대조한다. 시험한2MiB조각은로컬원본과정확히일치했다.

재개PID4522는01:14:55KST에시작했고,실제작업을기다리면서15초마다진행을출력하는노트북셀로감시한다. 기존상한**02:43:41KST**는연장하지않았다. [재개기록 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)과[마지막관측상태 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)는성능검증원장과구분한다. 자동점검150은정상진행에는조용히유지하고완료·실패·조치필요시에만알린다.

단계별학습ZIP·평가ZIP과실행환경·로그를보존하고,전체SHA·ZIP CRC·안전경로·내부파일목록·모든checkpoint·50epoch·교사연결·입력동일성을확인한후결과를등록한다. 실제로컬보존전에GPU런타임을삭제하지않는다. 이전대표30회·개발60회와과거탐색실험은덮어쓰지않는다.


### 2026-10-31 03:07 KST — 회수 검증과 A100 해제

후속 150개 학습과 신경망 4·5월 평가 250개가 정상 종료했다. 원격 실행의 학습·평가 경과 시간은 4,572.523초(약 76.21분)다. 단계별 원본 ZIP 10개와 환경·로그 ZIP 1개, 총 1,867,641,943바이트를 맥에 회수했다. 각 ZIP의 전체 SHA256, CRC, 안전한 경로, 내부 파일 해시와 실행별 계약을 검증했다. 신경망 학습의 50 epoch·초기값·대응 교사·입력 ID·체크포인트, 월별 예측과 재계산 지표가 모두 통과했다.

일반 다운로드가 작동하지 않아 노트북에 표시한 2MiB 조각을 브라우저로 읽어 복원했다. 따라서 GPU의 총 점유 시간에는 학습·평가 외에 회수와 확인 시간이 포함된다. 위 76.21분을 전체 GPU 과금 시간이라고 해석하면 안 된다. 회수 도중 브라우저 제어 실행 한 번이 시간 초과로 초기화되었으나 원격 Colab 세션과 로컬 조각 기록은 유지되어 저장된 위치부터 이어갔다. 학습 재실행은 없었다.

모든 원본의 실제 로컬 보존을 확인한 뒤 03:07 KST에 해당 A100의 연결 해제 및 런타임 삭제를 실행했다. UI의 `다시 연결 A100 / 연결하려면 클릭` 상태와 화면을 보존했다. 이후 GPU에 다시 연결하지 않고 로컬 M0 월별 평가 50개 → 후속 모델 150개 CPU 측정 → 통합 분석·발표 설명 → CPU 시연 확인 순서로 진행한다. 로컬 후처리 시작 PID는 72673이며 4시간 상한이다. 아직 이 단계까지 완료했다고 표기하지 않는다.

근거 파일: `continuation_recovered/recovery_complete.json`, `recovery_index.json`, 각 단계 `training_registry.json`·`evaluation_registry.json`, `operational_verification.json`, `runtime_release.json`, `a100_released.png`, `finalize_status.json`.

## 후속 결과 — 라벨 수·서비스 구성·CPU 비용

이 절의 수치는 로컬 회수·검증을 통과한 원본에서만 계산한다. 개발60fit·대표30fit·후속150fit은 서로 다른 실행이며, 소실된 미회수 시도를 완료 수에 더하지 않는다. ±는seed201~205의표본SD(ddof=1)이고신뢰구간이아니다.

<details><summary>mixed_n200 학습곡선·2월선택·시간</summary>


|run|선택F1(%)|선택epoch/round|완료epoch/round|마지막F1(%)|전체fit초|원본곡선|
|---|---|---|---|---|---|---|
|M0_s201_n200|49.229|138|168|48.717|10.49|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M0_s201_n200/metrics.json)|
|M1_s201_n200|66.123|20|50|65.699|49.23|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M1_s201_n200/metrics.json)|
|M2_s201_n200|70.474|43|50|70.416|39.68|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M2_s201_n200/metrics.json)|
|M3_s201_n200|46.274|40|50|45.628|6.83|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M3_s201_n200/metrics.json)|
|M4_s201_n200|46.189|40|50|45.990|7.60|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M4_s201_n200/metrics.json)|
|M5_s201_n200|45.778|44|50|45.475|7.62|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M5_s201_n200/metrics.json)|
|M0_s202_n200|48.532|94|124|48.177|5.22|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M0_s202_n200/metrics.json)|
|M1_s202_n200|67.009|49|50|66.741|40.54|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M1_s202_n200/metrics.json)|
|M2_s202_n200|70.435|37|50|70.301|39.82|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M2_s202_n200/metrics.json)|
|M3_s202_n200|44.302|46|50|44.103|6.82|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M3_s202_n200/metrics.json)|
|M4_s202_n200|44.338|44|50|44.115|7.64|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M4_s202_n200/metrics.json)|
|M5_s202_n200|45.222|46|50|45.104|7.70|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M5_s202_n200/metrics.json)|
|M0_s203_n200|49.488|102|132|49.311|5.57|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M0_s203_n200/metrics.json)|
|M1_s203_n200|65.772|24|50|65.315|40.15|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M1_s203_n200/metrics.json)|
|M2_s203_n200|70.569|40|50|70.220|39.78|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M2_s203_n200/metrics.json)|
|M3_s203_n200|44.009|46|50|43.806|6.84|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M3_s203_n200/metrics.json)|
|M4_s203_n200|43.701|40|50|43.620|7.68|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M4_s203_n200/metrics.json)|
|M5_s203_n200|43.817|45|50|43.684|7.60|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M5_s203_n200/metrics.json)|
|M0_s204_n200|48.566|81|111|48.555|4.56|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M0_s204_n200/metrics.json)|
|M1_s204_n200|66.888|20|50|66.143|40.31|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M1_s204_n200/metrics.json)|
|M2_s204_n200|69.144|35|50|69.056|39.84|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M2_s204_n200/metrics.json)|
|M3_s204_n200|45.099|39|50|44.679|6.80|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M3_s204_n200/metrics.json)|
|M4_s204_n200|45.464|39|50|45.460|7.66|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M4_s204_n200/metrics.json)|
|M5_s204_n200|45.776|39|50|45.521|7.66|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M5_s204_n200/metrics.json)|
|M0_s205_n200|50.340|180|210|49.922|9.20|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M0_s205_n200/metrics.json)|
|M1_s205_n200|68.412|33|50|67.992|40.33|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M1_s205_n200/metrics.json)|
|M2_s205_n200|71.703|46|50|71.556|39.92|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M2_s205_n200/metrics.json)|
|M3_s205_n200|44.021|47|50|43.894|6.80|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M3_s205_n200/metrics.json)|
|M4_s205_n200|44.571|37|50|44.237|7.63|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M4_s205_n200/metrics.json)|
|M5_s205_n200|44.327|45|50|44.021|7.66|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/main_recovered/training_0a6ed0ab2a84e29c/extracted/main_training/fits/M5_s205_n200/metrics.json)|

2월checkpoint선택값이며4·5월성능과구분한다. 마지막epoch선택만으로수렴을단정하지않고공통cosine일정과라벨별update수를함께해석한다. fit시간에는모델초기화·교사예측·학습·검증·checkpoint저장이포함된다.

</details>
<details><summary>mixed_n50 학습곡선·2월선택·시간</summary>


|run|선택F1(%)|선택epoch/round|완료epoch/round|마지막F1(%)|전체fit초|원본곡선|
|---|---|---|---|---|---|---|
|M0_s201_n50|40.568|65|95|40.368|5.71|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M0_s201_n50/metrics.json)|
|M1_s201_n50|55.476|33|50|55.018|21.76|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M1_s201_n50/metrics.json)|
|M2_s201_n50|56.133|50|50|56.133|14.35|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M2_s201_n50/metrics.json)|
|M3_s201_n50|28.514|46|50|28.213|2.68|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M3_s201_n50/metrics.json)|
|M4_s201_n50|28.714|46|50|28.341|2.97|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M4_s201_n50/metrics.json)|
|M5_s201_n50|28.782|47|50|28.766|2.94|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M5_s201_n50/metrics.json)|
|M0_s202_n50|39.956|203|233|39.821|6.16|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M0_s202_n50/metrics.json)|
|M1_s202_n50|52.198|31|50|52.095|14.12|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M1_s202_n50/metrics.json)|
|M2_s202_n50|56.597|50|50|56.597|14.43|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M2_s202_n50/metrics.json)|
|M3_s202_n50|26.454|35|50|26.300|2.57|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M3_s202_n50/metrics.json)|
|M4_s202_n50|25.636|42|50|25.590|2.95|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M4_s202_n50/metrics.json)|
|M5_s202_n50|25.930|43|50|25.880|2.97|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M5_s202_n50/metrics.json)|
|M0_s203_n50|39.727|107|137|39.493|3.61|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M0_s203_n50/metrics.json)|
|M1_s203_n50|54.175|21|50|53.405|13.54|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M1_s203_n50/metrics.json)|
|M2_s203_n50|54.390|47|50|54.364|14.67|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M2_s203_n50/metrics.json)|
|M3_s203_n50|25.750|44|50|25.523|2.60|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M3_s203_n50/metrics.json)|
|M4_s203_n50|25.621|46|50|25.389|2.89|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M4_s203_n50/metrics.json)|
|M5_s203_n50|26.281|37|50|25.909|2.91|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M5_s203_n50/metrics.json)|
|M0_s204_n50|40.634|67|97|39.935|2.45|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M0_s204_n50/metrics.json)|
|M1_s204_n50|53.716|25|50|53.385|13.56|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M1_s204_n50/metrics.json)|
|M2_s204_n50|53.731|45|50|53.703|14.28|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M2_s204_n50/metrics.json)|
|M3_s204_n50|26.663|47|50|26.649|2.59|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M3_s204_n50/metrics.json)|
|M4_s204_n50|26.265|49|50|26.244|2.99|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M4_s204_n50/metrics.json)|
|M5_s204_n50|27.233|44|50|27.052|2.91|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M5_s204_n50/metrics.json)|
|M0_s205_n50|41.060|150|180|40.946|4.82|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M0_s205_n50/metrics.json)|
|M1_s205_n50|53.378|28|50|52.946|13.66|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M1_s205_n50/metrics.json)|
|M2_s205_n50|55.158|48|50|55.156|14.19|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M2_s205_n50/metrics.json)|
|M3_s205_n50|25.229|45|50|24.959|2.60|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M3_s205_n50/metrics.json)|
|M4_s205_n50|25.062|46|50|24.948|2.99|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M4_s205_n50/metrics.json)|
|M5_s205_n50|25.822|43|50|25.506|2.93|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n50/training_51a644691955d138/extracted/continuation/mixed_n50/training/fits/M5_s205_n50/metrics.json)|

2월checkpoint선택값이며4·5월성능과구분한다. 마지막epoch선택만으로수렴을단정하지않고공통cosine일정과라벨별update수를함께해석한다. fit시간에는모델초기화·교사예측·학습·검증·checkpoint저장이포함된다.

</details>
<details><summary>mixed_n100 학습곡선·2월선택·시간</summary>


|run|선택F1(%)|선택epoch/round|완료epoch/round|마지막F1(%)|전체fit초|원본곡선|
|---|---|---|---|---|---|---|
|M0_s201_n100|45.357|136|166|45.275|5.89|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M0_s201_n100/metrics.json)|
|M1_s201_n100|61.436|43|50|61.252|22.88|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M1_s201_n100/metrics.json)|
|M2_s201_n100|64.872|46|50|64.775|22.84|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M2_s201_n100/metrics.json)|
|M3_s201_n100|37.434|45|50|37.411|4.02|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M3_s201_n100/metrics.json)|
|M4_s201_n100|37.986|46|50|37.835|4.56|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M4_s201_n100/metrics.json)|
|M5_s201_n100|37.959|38|50|37.828|4.47|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M5_s201_n100/metrics.json)|
|M0_s202_n100|45.135|176|206|44.827|7.36|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M0_s202_n100/metrics.json)|
|M1_s202_n100|60.464|30|50|60.380|22.50|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M1_s202_n100/metrics.json)|
|M2_s202_n100|65.325|44|50|65.232|22.85|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M2_s202_n100/metrics.json)|
|M3_s202_n100|34.719|44|50|34.545|4.02|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M3_s202_n100/metrics.json)|
|M4_s202_n100|34.425|43|50|34.249|4.56|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M4_s202_n100/metrics.json)|
|M5_s202_n100|35.013|42|50|34.949|4.57|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M5_s202_n100/metrics.json)|
|M0_s203_n100|43.317|77|107|43.112|3.61|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M0_s203_n100/metrics.json)|
|M1_s203_n100|60.011|27|50|59.904|22.63|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M1_s203_n100/metrics.json)|
|M2_s203_n100|63.917|45|50|63.893|22.74|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M2_s203_n100/metrics.json)|
|M3_s203_n100|35.603|46|50|35.479|3.98|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M3_s203_n100/metrics.json)|
|M4_s203_n100|35.820|42|50|35.568|4.51|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M4_s203_n100/metrics.json)|
|M5_s203_n100|35.611|42|50|35.207|4.59|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M5_s203_n100/metrics.json)|
|M0_s204_n100|44.217|99|129|43.948|4.49|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M0_s204_n100/metrics.json)|
|M1_s204_n100|61.405|24|50|60.540|22.59|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M1_s204_n100/metrics.json)|
|M2_s204_n100|63.916|50|50|63.916|23.00|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M2_s204_n100/metrics.json)|
|M3_s204_n100|37.603|44|50|37.256|4.09|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M3_s204_n100/metrics.json)|
|M4_s204_n100|37.397|40|50|37.172|4.53|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M4_s204_n100/metrics.json)|
|M5_s204_n100|38.683|40|50|38.472|4.49|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M5_s204_n100/metrics.json)|
|M0_s205_n100|45.881|159|189|45.680|6.72|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M0_s205_n100/metrics.json)|
|M1_s205_n100|61.612|34|50|61.391|22.46|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M1_s205_n100/metrics.json)|
|M2_s205_n100|65.950|34|50|65.889|22.57|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M2_s205_n100/metrics.json)|
|M3_s205_n100|37.506|39|50|37.491|4.00|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M3_s205_n100/metrics.json)|
|M4_s205_n100|37.242|39|50|36.499|4.50|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M4_s205_n100/metrics.json)|
|M5_s205_n100|36.580|34|50|35.983|4.45|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n100/training_a752b18aebfd41e5/extracted/continuation/mixed_n100/training/fits/M5_s205_n100/metrics.json)|

2월checkpoint선택값이며4·5월성능과구분한다. 마지막epoch선택만으로수렴을단정하지않고공통cosine일정과라벨별update수를함께해석한다. fit시간에는모델초기화·교사예측·학습·검증·checkpoint저장이포함된다.

</details>
<details><summary>mixed_n1000 학습곡선·2월선택·시간</summary>


|run|선택F1(%)|선택epoch/round|완료epoch/round|마지막F1(%)|전체fit초|원본곡선|
|---|---|---|---|---|---|---|
|M0_s201_n1000|55.919|201|231|55.588|16.61|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M0_s201_n1000/metrics.json)|
|M1_s201_n1000|75.343|36|50|74.574|183.47|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M1_s201_n1000/metrics.json)|
|M2_s201_n1000|79.420|41|50|79.190|178.73|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M2_s201_n1000/metrics.json)|
|M3_s201_n1000|60.199|45|50|59.944|29.00|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M3_s201_n1000/metrics.json)|
|M4_s201_n1000|60.117|37|50|59.797|33.11|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M4_s201_n1000/metrics.json)|
|M5_s201_n1000|60.271|45|50|60.118|33.27|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M5_s201_n1000/metrics.json)|
|M0_s202_n1000|56.658|284|314|56.531|23.01|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M0_s202_n1000/metrics.json)|
|M1_s202_n1000|74.745|30|50|73.621|184.41|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M1_s202_n1000/metrics.json)|
|M2_s202_n1000|77.810|34|50|77.561|179.43|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M2_s202_n1000/metrics.json)|
|M3_s202_n1000|61.289|42|50|61.121|29.76|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M3_s202_n1000/metrics.json)|
|M4_s202_n1000|61.416|41|50|61.100|32.65|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M4_s202_n1000/metrics.json)|
|M5_s202_n1000|60.902|49|50|60.895|33.22|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M5_s202_n1000/metrics.json)|
|M0_s203_n1000|55.949|184|214|55.629|15.61|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M0_s203_n1000/metrics.json)|
|M1_s203_n1000|75.381|26|50|75.031|182.93|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M1_s203_n1000/metrics.json)|
|M2_s203_n1000|77.637|36|50|77.335|178.07|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M2_s203_n1000/metrics.json)|
|M3_s203_n1000|59.297|41|50|58.885|29.54|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M3_s203_n1000/metrics.json)|
|M4_s203_n1000|59.417|49|50|59.408|33.02|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M4_s203_n1000/metrics.json)|
|M5_s203_n1000|60.070|50|50|60.070|32.79|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M5_s203_n1000/metrics.json)|
|M0_s204_n1000|55.385|181|211|55.061|15.29|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M0_s204_n1000/metrics.json)|
|M1_s204_n1000|74.899|49|50|74.722|183.07|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M1_s204_n1000/metrics.json)|
|M2_s204_n1000|78.564|34|50|77.997|178.31|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M2_s204_n1000/metrics.json)|
|M3_s204_n1000|60.772|42|50|60.158|29.22|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M3_s204_n1000/metrics.json)|
|M4_s204_n1000|60.181|36|50|59.611|32.69|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M4_s204_n1000/metrics.json)|
|M5_s204_n1000|60.982|44|50|60.856|32.63|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M5_s204_n1000/metrics.json)|
|M0_s205_n1000|57.572|324|354|57.429|24.84|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M0_s205_n1000/metrics.json)|
|M1_s205_n1000|75.744|10|50|74.894|182.62|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M1_s205_n1000/metrics.json)|
|M2_s205_n1000|79.312|33|50|79.120|178.98|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M2_s205_n1000/metrics.json)|
|M3_s205_n1000|59.824|44|50|59.608|29.10|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M3_s205_n1000/metrics.json)|
|M4_s205_n1000|60.290|44|50|59.937|32.78|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M4_s205_n1000/metrics.json)|
|M5_s205_n1000|59.900|43|50|59.795|32.66|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/mixed_n1000/training_df150d74a25ff1f5/extracted/continuation/mixed_n1000/training/fits/M5_s205_n1000/metrics.json)|

2월checkpoint선택값이며4·5월성능과구분한다. 마지막epoch선택만으로수렴을단정하지않고공통cosine일정과라벨별update수를함께해석한다. fit시간에는모델초기화·교사예측·학습·검증·checkpoint저장이포함된다.

</details>
<details><summary>nongoogle_n200 학습곡선·2월선택·시간</summary>


|run|선택F1(%)|선택epoch/round|완료epoch/round|마지막F1(%)|전체fit초|원본곡선|
|---|---|---|---|---|---|---|
|M0_s201_n200|78.286|84|114|78.015|1.90|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M0_s201_n200/metrics.json)|
|M1_s201_n200|91.469|41|50|91.307|27.67|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M1_s201_n200/metrics.json)|
|M2_s201_n200|93.057|36|50|92.873|27.12|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M2_s201_n200/metrics.json)|
|M3_s201_n200|64.463|39|50|64.258|4.65|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M3_s201_n200/metrics.json)|
|M4_s201_n200|64.498|39|50|64.026|5.21|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M4_s201_n200/metrics.json)|
|M5_s201_n200|65.743|39|50|65.498|5.22|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M5_s201_n200/metrics.json)|
|M0_s202_n200|79.321|131|161|79.119|2.82|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M0_s202_n200/metrics.json)|
|M1_s202_n200|91.234|29|50|91.155|27.48|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M1_s202_n200/metrics.json)|
|M2_s202_n200|93.078|31|50|92.913|26.96|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M2_s202_n200/metrics.json)|
|M3_s202_n200|65.536|42|50|65.382|4.59|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M3_s202_n200/metrics.json)|
|M4_s202_n200|65.242|41|50|64.870|5.24|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M4_s202_n200/metrics.json)|
|M5_s202_n200|65.034|42|50|64.974|5.18|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M5_s202_n200/metrics.json)|
|M0_s203_n200|78.326|150|180|78.161|3.28|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M0_s203_n200/metrics.json)|
|M1_s203_n200|91.233|17|50|90.996|27.29|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M1_s203_n200/metrics.json)|
|M2_s203_n200|92.791|41|50|92.713|27.33|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M2_s203_n200/metrics.json)|
|M3_s203_n200|63.642|47|50|63.365|4.62|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M3_s203_n200/metrics.json)|
|M4_s203_n200|64.394|50|50|64.394|5.23|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M4_s203_n200/metrics.json)|
|M5_s203_n200|64.084|48|50|63.826|5.25|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M5_s203_n200/metrics.json)|
|M0_s204_n200|77.403|103|133|76.983|2.32|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M0_s204_n200/metrics.json)|
|M1_s204_n200|91.528|25|50|91.179|27.46|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M1_s204_n200/metrics.json)|
|M2_s204_n200|92.956|29|50|92.662|26.96|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M2_s204_n200/metrics.json)|
|M3_s204_n200|66.826|45|50|66.540|4.60|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M3_s204_n200/metrics.json)|
|M4_s204_n200|66.289|45|50|65.999|5.21|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M4_s204_n200/metrics.json)|
|M5_s204_n200|66.765|49|50|66.729|5.27|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M5_s204_n200/metrics.json)|
|M0_s205_n200|78.227|67|97|77.474|1.59|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M0_s205_n200/metrics.json)|
|M1_s205_n200|91.464|31|50|91.265|27.57|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M1_s205_n200/metrics.json)|
|M2_s205_n200|92.984|43|50|92.828|27.07|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M2_s205_n200/metrics.json)|
|M3_s205_n200|61.585|45|50|61.434|4.62|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M3_s205_n200/metrics.json)|
|M4_s205_n200|61.909|49|50|61.824|5.28|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M4_s205_n200/metrics.json)|
|M5_s205_n200|63.389|47|50|63.260|5.28|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/nongoogle_n200/training_ce7744b1f97a6366/extracted/continuation/nongoogle_n200/training/fits/M5_s205_n200/metrics.json)|

2월checkpoint선택값이며4·5월성능과구분한다. 마지막epoch선택만으로수렴을단정하지않고공통cosine일정과라벨별update수를함께해석한다. fit시간에는모델초기화·교사예측·학습·검증·checkpoint저장이포함된다.

</details>
<details><summary>googleonly_n200 학습곡선·2월선택·시간</summary>


|run|선택F1(%)|선택epoch/round|완료epoch/round|마지막F1(%)|전체fit초|원본곡선|
|---|---|---|---|---|---|---|
|M0_s201_n200|39.698|159|189|39.274|8.69|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M0_s201_n200/metrics.json)|
|M1_s201_n200|59.376|27|50|58.281|40.71|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M1_s201_n200/metrics.json)|
|M2_s201_n200|63.414|41|50|63.148|40.05|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M2_s201_n200/metrics.json)|
|M3_s201_n200|35.092|38|50|34.865|6.88|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M3_s201_n200/metrics.json)|
|M4_s201_n200|34.311|38|50|33.870|7.75|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M4_s201_n200/metrics.json)|
|M5_s201_n200|35.494|40|50|35.325|7.67|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M5_s201_n200/metrics.json)|
|M0_s202_n200|40.315|101|131|40.040|5.85|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M0_s202_n200/metrics.json)|
|M1_s202_n200|59.970|34|50|59.079|40.35|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M1_s202_n200/metrics.json)|
|M2_s202_n200|62.569|37|50|62.310|39.68|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M2_s202_n200/metrics.json)|
|M3_s202_n200|35.119|45|50|34.936|6.82|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M3_s202_n200/metrics.json)|
|M4_s202_n200|34.969|33|50|34.399|7.73|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M4_s202_n200/metrics.json)|
|M5_s202_n200|35.602|33|50|35.175|7.73|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M5_s202_n200/metrics.json)|
|M0_s203_n200|39.751|79|109|39.623|4.69|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M0_s203_n200/metrics.json)|
|M1_s203_n200|59.689|32|50|59.219|40.51|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M1_s203_n200/metrics.json)|
|M2_s203_n200|65.409|44|50|65.295|39.84|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M2_s203_n200/metrics.json)|
|M3_s203_n200|34.069|43|50|33.880|6.82|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M3_s203_n200/metrics.json)|
|M4_s203_n200|34.171|45|50|33.718|7.81|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M4_s203_n200/metrics.json)|
|M5_s203_n200|34.908|44|50|34.536|7.84|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M5_s203_n200/metrics.json)|
|M0_s204_n200|39.405|99|129|39.005|5.73|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M0_s204_n200/metrics.json)|
|M1_s204_n200|57.696|35|50|57.429|40.29|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M1_s204_n200/metrics.json)|
|M2_s204_n200|63.760|35|50|63.557|39.88|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M2_s204_n200/metrics.json)|
|M3_s204_n200|33.232|46|50|33.129|6.92|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M3_s204_n200/metrics.json)|
|M4_s204_n200|32.738|47|50|32.599|7.79|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M4_s204_n200/metrics.json)|
|M5_s204_n200|34.167|48|50|34.085|7.72|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M5_s204_n200/metrics.json)|
|M0_s205_n200|40.239|157|187|40.211|8.57|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M0_s205_n200/metrics.json)|
|M1_s205_n200|60.377|15|50|59.572|40.45|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M1_s205_n200/metrics.json)|
|M2_s205_n200|62.490|37|50|62.308|40.03|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M2_s205_n200/metrics.json)|
|M3_s205_n200|32.691|49|50|32.689|6.99|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M3_s205_n200/metrics.json)|
|M4_s205_n200|32.784|39|50|32.707|7.72|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M4_s205_n200/metrics.json)|
|M5_s205_n200|33.688|47|50|33.680|7.72|[전체epoch와설정](../../experiments/2026-10-30_midterm_restart/continuation_recovered/googleonly_n200/training_7e6253252c0ee856/extracted/continuation/googleonly_n200/training/fits/M5_s205_n200/metrics.json)|

2월checkpoint선택값이며4·5월성능과구분한다. 마지막epoch선택만으로수렴을단정하지않고공통cosine일정과라벨별update수를함께해석한다. fit시간에는모델초기화·교사예측·학습·검증·checkpoint저장이포함된다.

</details>

|조건|서비스구성|클래스당표본|학습|월별평가|CPU모델측정|
|---|---|---|---|---|---|
|mixed_n200|google_included20|200|30/30|60/60|30/30|
|mixed_n50|google_included20|50|30/30|60/60|30/30|
|mixed_n100|google_included20|100|30/30|60/60|30/30|
|mixed_n1000|google_included20|1000|30/30|60/60|30/30|
|nongoogle_n200|non_google13|200|30/30|60/60|30/30|
|googleonly_n200|google_only20|200|30/30|60/60|30/30|

### 202504 전체 평가 — 모델별 Macro-F1


|조건|M0|M1|M2|M3|M4|M5|
|---|---|---|---|---|---|---|
|mixed_n200|34.075 ± 0.379|50.332 ± 1.617|53.771 ± 1.743|32.493 ± 0.982|32.451 ± 0.736|32.743 ± 0.815|
|mixed_n50|29.233 ± 0.982|40.651 ± 1.032|42.319 ± 1.691|19.088 ± 0.886|18.909 ± 0.866|19.475 ± 0.902|
|mixed_n100|31.830 ± 0.691|46.675 ± 0.322|49.310 ± 1.721|26.140 ± 0.819|26.310 ± 0.837|26.463 ± 0.921|
|mixed_n1000|38.623 ± 0.334|58.396 ± 1.181|62.475 ± 0.820|46.098 ± 0.243|46.423 ± 0.489|46.342 ± 0.599|
|nongoogle_n200|62.369 ± 0.503|78.208 ± 1.273|80.171 ± 1.549|47.855 ± 2.517|47.899 ± 2.399|48.194 ± 1.684|
|googleonly_n200|17.746 ± 0.148|32.216 ± 2.591|36.625 ± 2.087|16.116 ± 1.532|16.077 ± 1.824|16.643 ± 1.512|

### 202504 같은 seed의 대응 차이(%p)

|조건|비교|201|202|203|204|205|평균±SD|양수반복|
|---|---|---|---|---|---|---|---|---|
|mixed_n200|M2−M1|+4.731|+4.775|+4.446|-1.482|+4.728|3.439 ± 2.754|4/5|
|mixed_n200|M4−M3|-0.412|-0.063|+0.545|+0.118|-0.398|-0.042 ± 0.398|2/5|
|mixed_n200|M5−M3|-0.593|+0.378|+0.333|+0.739|+0.394|0.250 ± 0.499|4/5|
|mixed_n200|M5−M4|-0.181|+0.441|-0.212|+0.621|+0.792|0.292 ± 0.463|3/5|
|mixed_n200|M2−M5|+20.176|+20.804|+22.989|+17.783|+23.390|21.028 ± 2.276|5/5|
|mixed_n50|M2−M1|+2.878|+3.728|+0.377|-1.884|+3.239|1.667 ± 2.370|4/5|
|mixed_n50|M4−M3|+0.191|-0.865|-0.142|-0.448|+0.367|-0.179 ± 0.495|2/5|
|mixed_n50|M5−M3|+0.175|-0.187|+0.698|+0.795|+0.452|0.387 ± 0.400|4/5|
|mixed_n50|M5−M4|-0.016|+0.678|+0.840|+1.243|+0.085|0.566 ± 0.528|4/5|
|mixed_n50|M2−M5|+23.276|+23.883|+22.924|+18.961|+25.177|22.844 ± 2.334|5/5|
|mixed_n100|M2−M1|+2.745|+3.139|+3.047|-0.634|+4.882|2.636 ± 2.011|4/5|
|mixed_n100|M4−M3|+0.510|+0.149|+0.150|+0.298|-0.257|0.170 ± 0.281|4/5|
|mixed_n100|M5−M3|+0.176|+0.840|+0.219|+1.204|-0.824|0.323 ± 0.773|4/5|
|mixed_n100|M5−M4|-0.335|+0.691|+0.069|+0.906|-0.567|0.153 ± 0.636|3/5|
|mixed_n100|M2−M5|+22.653|+23.719|+24.059|+18.567|+25.239|22.847 ± 2.564|5/5|
|mixed_n1000|M2−M1|+4.443|+4.649|+2.651|+3.115|+5.537|4.079 ± 1.178|5/5|
|mixed_n1000|M4−M3|+0.473|+0.775|+0.794|+0.195|-0.613|0.325 ± 0.579|4/5|
|mixed_n1000|M5−M3|+0.702|+0.341|+0.525|+0.398|-0.744|0.244 ± 0.570|4/5|
|mixed_n1000|M5−M4|+0.230|-0.434|-0.269|+0.202|-0.131|-0.080 ± 0.291|2/5|
|mixed_n1000|M2−M5|+15.525|+15.430|+16.196|+15.303|+18.212|16.133 ± 1.212|5/5|
|nongoogle_n200|M2−M1|+0.181|+2.187|+5.085|+0.855|+1.508|1.963 ± 1.898|5/5|
|nongoogle_n200|M4−M3|+0.117|-0.489|+0.615|-0.055|+0.030|0.044 ± 0.395|3/5|
|nongoogle_n200|M5−M3|+0.846|-1.060|+0.385|-0.256|+1.780|0.339 ± 1.078|3/5|
|nongoogle_n200|M5−M4|+0.729|-0.571|-0.230|-0.201|+1.750|0.295 ± 0.946|2/5|
|nongoogle_n200|M2−M5|+28.621|+32.633|+33.714|+29.581|+35.334|31.977 ± 2.816|5/5|
|googleonly_n200|M2−M1|+7.963|+2.114|+6.593|+7.455|-2.081|4.409 ± 4.303|4/5|
|googleonly_n200|M4−M3|+0.142|+0.388|-0.024|-0.557|-0.143|-0.039 ± 0.351|2/5|
|googleonly_n200|M5−M3|+0.040|+0.962|+0.158|+0.508|+0.967|0.527 ± 0.435|5/5|
|googleonly_n200|M5−M4|-0.101|+0.574|+0.183|+1.064|+1.110|0.566 ± 0.533|4/5|
|googleonly_n200|M2−M5|+21.280|+15.786|+22.537|+21.298|+19.009|19.982 ± 2.669|5/5|

### 202505 전체 평가 — 모델별 Macro-F1


|조건|M0|M1|M2|M3|M4|M5|
|---|---|---|---|---|---|---|
|mixed_n200|34.248 ± 0.423|50.148 ± 1.661|53.680 ± 1.456|32.777 ± 0.975|32.716 ± 0.697|32.990 ± 0.805|
|mixed_n50|29.513 ± 0.939|40.766 ± 0.831|42.151 ± 1.540|19.299 ± 0.876|19.133 ± 0.858|19.689 ± 0.914|
|mixed_n100|32.049 ± 0.617|46.533 ± 0.294|49.379 ± 1.473|26.386 ± 0.829|26.578 ± 0.832|26.697 ± 0.895|
|mixed_n1000|38.761 ± 0.352|57.836 ± 1.042|62.159 ± 0.693|45.893 ± 0.236|46.194 ± 0.571|46.176 ± 0.645|
|nongoogle_n200|62.934 ± 0.279|76.652 ± 0.982|79.062 ± 1.756|48.137 ± 2.402|48.217 ± 2.300|48.453 ± 1.634|
|googleonly_n200|17.205 ± 0.207|31.563 ± 2.477|36.265 ± 1.651|15.848 ± 1.567|15.827 ± 1.885|16.346 ± 1.556|

### 202505 같은 seed의 대응 차이(%p)

|조건|비교|201|202|203|204|205|평균±SD|양수반복|
|---|---|---|---|---|---|---|---|---|
|mixed_n200|M2−M1|+5.096|+4.853|+4.142|-1.071|+4.641|3.532 ± 2.597|4/5|
|mixed_n200|M4−M3|-0.471|-0.082|+0.530|+0.143|-0.427|-0.062 ± 0.417|2/5|
|mixed_n200|M5−M3|-0.658|+0.361|+0.366|+0.730|+0.264|0.213 ± 0.518|4/5|
|mixed_n200|M5−M4|-0.186|+0.443|-0.163|+0.587|+0.692|0.274 ± 0.420|3/5|
|mixed_n200|M2−M5|+20.207|+20.402|+22.169|+17.915|+22.758|20.690 ± 1.903|5/5|
|mixed_n50|M2−M1|+2.778|+3.085|-0.255|-1.567|+2.883|1.385 ± 2.149|3/5|
|mixed_n50|M4−M3|+0.191|-0.828|-0.098|-0.413|+0.316|-0.167 ± 0.465|2/5|
|mixed_n50|M5−M3|+0.182|-0.113|+0.718|+0.765|+0.399|0.390 ± 0.369|4/5|
|mixed_n50|M5−M4|-0.009|+0.716|+0.817|+1.178|+0.083|0.557 ± 0.506|4/5|
|mixed_n50|M2−M5|+23.155|+23.531|+21.956|+19.018|+24.650|22.462 ± 2.152|5/5|
|mixed_n100|M2−M1|+3.184|+2.819|+3.212|+0.059|+4.958|2.846 ± 1.766|5/5|
|mixed_n100|M4−M3|+0.465|+0.162|+0.205|+0.331|-0.201|0.193 ± 0.249|4/5|
|mixed_n100|M5−M3|+0.211|+0.745|+0.188|+1.176|-0.765|0.311 ± 0.728|4/5|
|mixed_n100|M5−M4|-0.254|+0.582|-0.017|+0.845|-0.564|0.119 ± 0.584|2/5|
|mixed_n100|M2−M5|+22.669|+23.347|+23.755|+18.937|+24.704|22.682 ± 2.219|5/5|
|mixed_n1000|M2−M1|+5.065|+4.358|+2.412|+3.758|+6.023|4.323 ± 1.361|5/5|
|mixed_n1000|M4−M3|+0.515|+0.650|+0.750|+0.218|-0.628|0.301 ± 0.556|4/5|
|mixed_n1000|M5−M3|+0.535|+0.317|+0.723|+0.511|-0.667|0.284 ± 0.551|4/5|
|mixed_n1000|M5−M4|+0.020|-0.333|-0.027|+0.293|-0.039|-0.017 ± 0.222|2/5|
|mixed_n1000|M2−M5|+15.720|+15.463|+15.486|+15.139|+18.105|15.983 ± 1.204|5/5|
|nongoogle_n200|M2−M1|+1.142|+3.050|+5.736|+0.583|+1.542|2.411 ± 2.072|5/5|
|nongoogle_n200|M4−M3|+0.069|-0.458|+0.638|+0.094|+0.055|0.080 ± 0.388|4/5|
|nongoogle_n200|M5−M3|+0.840|-0.906|+0.199|-0.210|+1.655|0.316 ± 0.981|3/5|
|nongoogle_n200|M5−M4|+0.771|-0.448|-0.439|-0.304|+1.600|0.236 ± 0.917|2/5|
|nongoogle_n200|M2−M5|+27.664|+31.238|+33.042|+27.762|+33.343|30.610 ± 2.764|5/5|
|googleonly_n200|M2−M1|+7.631|+2.593|+6.249|+7.857|-0.818|4.702 ± 3.736|4/5|
|googleonly_n200|M4−M3|+0.252|+0.406|-0.008|-0.698|-0.057|-0.021 ± 0.424|2/5|
|googleonly_n200|M5−M3|-0.011|+1.006|+0.085|+0.496|+0.914|0.498 ± 0.464|4/5|
|googleonly_n200|M5−M4|-0.263|+0.600|+0.093|+1.194|+0.971|0.519 ± 0.604|4/5|
|googleonly_n200|M2−M5|+20.759|+15.689|+21.859|+21.371|+19.918|19.919 ± 2.473|5/5|


M2−M1은명시한BN적응정책을포함한사전학습활용비교다. M5−M3이증류의추가효과이고, M2−M5는교사대비학생의성능차이다. 5개차이의부호와크기를함께보며유의성검정없이확정적우위라고말하지않는다.

### 목표와 해석의 한계

- mixed_n200: 교사대비학생F1차이평균 21.028%p; 2%p이내반복 0/5. 평균기준목표 미달.
- mixed_n50: 교사대비학생F1차이평균 22.844%p; 2%p이내반복 0/5. 평균기준목표 미달.
- mixed_n100: 교사대비학생F1차이평균 22.847%p; 2%p이내반복 0/5. 평균기준목표 미달.
- mixed_n1000: 교사대비학생F1차이평균 16.133%p; 2%p이내반복 0/5. 평균기준목표 미달.
- nongoogle_n200: 교사대비학생F1차이평균 31.977%p; 2%p이내반복 0/5. 평균기준목표 미달.
- googleonly_n200: 교사대비학생F1차이평균 19.982%p; 2%p이내반복 0/5. 평균기준목표 미달.

라벨수가늘면공통50epoch에서도update와학습시간이늘어난다. 서비스구성별클래스수·목록·난이도도다르므로점수차이를Google여부하나의인과효과로해석하지않는다. 4·5월은과거에도살펴본시간차평가자료로완전히미사용외부최종검증이아니다.

### CPU 추론 비용

모델마다새프로세스,CPU1스레드·FP32·고정128입력순환·동일warm-up/반복규칙이다. p95평균은모든지연을합친p95가아니다. M0에는16통계추출이포함되며패킷수집대기·파일IO·array변환은제외한다. 입력은20클래스6~7개씩,13클래스9~10개씩총128개로균등에가깝게고정했다. 구성간서로다른입력과시스템부하가있어작은속도차이를모델고유차이로단정하지않는다.

|조건|모델|batch1중앙값평균±SD(ms)|개별p95평균±SD(ms)|128묶음처리량평균±SD(flows/s)|추론파일MiB평균±SD|
|---|---|---|---|---|---|
|mixed_n200|M0|0.310 ± 0.068|0.386 ± 0.103|7571.075 ± 2588.734|7.229 ± 2.479|
|mixed_n200|M1|0.350 ± 0.003|0.417 ± 0.030|97.599 ± 4.573|2.724 ± 0.000|
|mixed_n200|M2|0.353 ± 0.006|0.571 ± 0.231|98.786 ± 5.504|2.724 ± 0.000|
|mixed_n200|M3|0.040 ± 0.001|0.058 ± 0.028|6986.028 ± 276.718|0.080 ± 0.000|
|mixed_n200|M4|0.040 ± 0.000|0.049 ± 0.005|7100.589 ± 260.879|0.080 ± 0.000|
|mixed_n200|M5|0.040 ± 0.000|0.065 ± 0.038|7035.760 ± 256.572|0.080 ± 0.000|
|mixed_n50|M0|0.245 ± 0.047|0.269 ± 0.051|14155.164 ± 7283.033|4.777 ± 2.451|
|mixed_n50|M1|0.341 ± 0.002|0.364 ± 0.001|105.964 ± 0.777|2.724 ± 0.000|
|mixed_n50|M2|0.341 ± 0.001|0.365 ± 0.003|105.858 ± 0.406|2.724 ± 0.000|
|mixed_n50|M3|0.039 ± 0.000|0.043 ± 0.001|7328.265 ± 171.065|0.080 ± 0.000|
|mixed_n50|M4|0.040 ± 0.001|0.063 ± 0.042|7354.325 ± 102.941|0.080 ± 0.000|
|mixed_n50|M5|0.040 ± 0.000|0.044 ± 0.001|7404.883 ± 22.205|0.080 ± 0.000|
|mixed_n100|M0|0.295 ± 0.046|0.428 ± 0.225|8691.099 ± 3331.521|7.553 ± 2.461|
|mixed_n100|M1|0.343 ± 0.003|0.370 ± 0.012|105.983 ± 0.425|2.724 ± 0.000|
|mixed_n100|M2|0.342 ± 0.001|0.385 ± 0.038|103.601 ± 3.045|2.724 ± 0.000|
|mixed_n100|M3|0.040 ± 0.000|0.043 ± 0.001|7503.776 ± 49.833|0.080 ± 0.000|
|mixed_n100|M4|0.040 ± 0.000|0.043 ± 0.001|7361.414 ± 78.658|0.080 ± 0.000|
|mixed_n100|M5|0.040 ± 0.000|0.043 ± 0.001|7399.020 ± 213.332|0.080 ± 0.000|
|mixed_n1000|M0|0.395 ± 0.085|0.630 ± 0.495|4929.572 ± 1435.431|14.861 ± 4.202|
|mixed_n1000|M1|0.343 ± 0.002|0.366 ± 0.002|106.281 ± 1.305|2.724 ± 0.000|
|mixed_n1000|M2|0.343 ± 0.002|0.365 ± 0.004|106.039 ± 1.226|2.724 ± 0.000|
|mixed_n1000|M3|0.039 ± 0.001|0.043 ± 0.001|7319.283 ± 216.838|0.080 ± 0.000|
|mixed_n1000|M4|0.040 ± 0.000|0.043 ± 0.001|7298.016 ± 182.228|0.080 ± 0.000|
|mixed_n1000|M5|0.040 ± 0.000|0.043 ± 0.001|7331.804 ± 130.455|0.080 ± 0.000|
|nongoogle_n200|M0|0.203 ± 0.020|0.228 ± 0.021|24616.563 ± 10422.290|3.753 ± 1.240|
|nongoogle_n200|M1|0.335 ± 0.001|0.358 ± 0.004|105.023 ± 0.740|2.712 ± 0.000|
|nongoogle_n200|M2|0.333 ± 0.006|0.487 ± 0.285|105.259 ± 1.678|2.712 ± 0.000|
|nongoogle_n200|M3|0.040 ± 0.000|0.043 ± 0.001|7424.608 ± 40.047|0.078 ± 0.000|
|nongoogle_n200|M4|0.039 ± 0.000|0.042 ± 0.001|7369.923 ± 143.331|0.078 ± 0.000|
|nongoogle_n200|M5|0.039 ± 0.001|0.045 ± 0.002|7116.770 ± 688.395|0.078 ± 0.000|
|googleonly_n200|M0|0.302 ± 0.053|0.334 ± 0.065|8061.180 ± 3065.893|7.726 ± 2.407|
|googleonly_n200|M1|0.340 ± 0.002|0.359 ± 0.007|107.620 ± 0.263|2.724 ± 0.000|
|googleonly_n200|M2|0.343 ± 0.003|0.359 ± 0.006|106.816 ± 0.511|2.724 ± 0.000|
|googleonly_n200|M3|0.040 ± 0.000|0.043 ± 0.001|7431.303 ± 22.337|0.080 ± 0.000|
|googleonly_n200|M4|0.039 ± 0.000|0.042 ± 0.001|7416.728 ± 7.608|0.080 ± 0.000|
|googleonly_n200|M5|0.040 ± 0.000|0.042 ± 0.001|7422.289 ± 6.613|0.080 ± 0.000|

<details><summary>mixed_n200 전체·겹침·비겹침·공통미관측</summary>


|월|부분집합|모델|N범위|support있는클래스범위|F1평균±SD(%)|정확도평균±SD(%)|
|---|---|---|---|---|---|---|
|202504|all|M0|379194–379194|20–20|34.075 ± 0.379|47.078 ± 0.493|
|202504|all|M1|379194–379194|20–20|50.332 ± 1.617|65.000 ± 1.685|
|202504|all|M2|379194–379194|20–20|53.771 ± 1.743|69.563 ± 1.304|
|202504|all|M3|379194–379194|20–20|32.493 ± 0.982|45.536 ± 0.920|
|202504|all|M4|379194–379194|20–20|32.451 ± 0.736|45.347 ± 0.949|
|202504|all|M5|379194–379194|20–20|32.743 ± 0.815|45.935 ± 0.689|
|202504|train_overlap|M0|0–7|0–4|N/A|N/A|
|202504|train_overlap|M1|0–7|0–4|N/A|N/A|
|202504|train_overlap|M2|0–7|0–4|N/A|N/A|
|202504|train_overlap|M3|0–7|0–4|N/A|N/A|
|202504|train_overlap|M4|0–7|0–4|N/A|N/A|
|202504|train_overlap|M5|0–7|0–4|N/A|N/A|
|202504|train_nonoverlap|M0|379187–379194|20–20|34.075 ± 0.380|47.078 ± 0.493|
|202504|train_nonoverlap|M1|379187–379194|20–20|50.332 ± 1.617|65.000 ± 1.685|
|202504|train_nonoverlap|M2|379187–379194|20–20|53.771 ± 1.743|69.564 ± 1.305|
|202504|train_nonoverlap|M3|379187–379194|20–20|32.493 ± 0.982|45.536 ± 0.920|
|202504|train_nonoverlap|M4|379187–379194|20–20|32.451 ± 0.736|45.348 ± 0.949|
|202504|train_nonoverlap|M5|379187–379194|20–20|32.743 ± 0.815|45.936 ± 0.690|
|202504|common_unseen|M0|376465–376465|20–20|34.215 ± 0.414|47.373 ± 0.496|
|202504|common_unseen|M1|376465–376465|20–20|50.575 ± 1.678|65.335 ± 1.777|
|202504|common_unseen|M2|376465–376465|20–20|54.020 ± 1.634|69.968 ± 1.287|
|202504|common_unseen|M3|376465–376465|20–20|32.702 ± 0.942|45.767 ± 0.920|
|202504|common_unseen|M4|376465–376465|20–20|32.698 ± 0.717|45.666 ± 0.952|
|202504|common_unseen|M5|376465–376465|20–20|32.955 ± 0.700|46.191 ± 0.640|
|202505|all|M0|365258–365258|20–20|34.248 ± 0.423|46.162 ± 0.516|
|202505|all|M1|365258–365258|20–20|50.148 ± 1.661|64.412 ± 1.689|
|202505|all|M2|365258–365258|20–20|53.680 ± 1.456|69.013 ± 1.099|
|202505|all|M3|365258–365258|20–20|32.777 ± 0.975|44.757 ± 1.031|
|202505|all|M4|365258–365258|20–20|32.716 ± 0.697|44.560 ± 1.074|
|202505|all|M5|365258–365258|20–20|32.990 ± 0.805|45.149 ± 0.736|
|202505|train_overlap|M0|2–6|1–4|4.000 ± 4.183|35.000 ± 41.833|
|202505|train_overlap|M1|2–6|1–4|4.000 ± 4.183|35.000 ± 41.833|
|202505|train_overlap|M2|2–6|1–4|4.000 ± 4.183|35.000 ± 41.833|
|202505|train_overlap|M3|2–6|1–4|3.000 ± 4.472|30.000 ± 44.721|
|202505|train_overlap|M4|2–6|1–4|3.000 ± 4.472|30.000 ± 44.721|
|202505|train_overlap|M5|2–6|1–4|3.000 ± 4.472|30.000 ± 44.721|
|202505|train_nonoverlap|M0|365252–365256|20–20|34.248 ± 0.422|46.162 ± 0.516|
|202505|train_nonoverlap|M1|365252–365256|20–20|50.148 ± 1.661|64.413 ± 1.689|
|202505|train_nonoverlap|M2|365252–365256|20–20|53.681 ± 1.456|69.013 ± 1.099|
|202505|train_nonoverlap|M3|365252–365256|20–20|32.777 ± 0.975|44.757 ± 1.031|
|202505|train_nonoverlap|M4|365252–365256|20–20|32.716 ± 0.698|44.560 ± 1.074|
|202505|train_nonoverlap|M5|365252–365256|20–20|32.990 ± 0.805|45.149 ± 0.737|
|202505|common_unseen|M0|362640–362640|20–20|34.377 ± 0.447|46.420 ± 0.515|
|202505|common_unseen|M1|362640–362640|20–20|50.381 ± 1.717|64.724 ± 1.777|
|202505|common_unseen|M2|362640–362640|20–20|53.909 ± 1.382|69.392 ± 1.103|
|202505|common_unseen|M3|362640–362640|20–20|32.983 ± 0.939|44.976 ± 1.025|
|202505|common_unseen|M4|362640–362640|20–20|32.964 ± 0.688|44.873 ± 1.079|
|202505|common_unseen|M5|362640–362640|20–20|33.205 ± 0.704|45.398 ± 0.685|

빈부분집합은N/A. 고정클래스수에서support없는클래스처리규칙을유지한다. 희소겹침집단은전체서비스성능추정이아니다.

</details>
<details><summary>mixed_n200 서비스별F1과교사·학생의주요혼동</summary>


|월|서비스|support|M0|M1|M2|M3|M4|M5|
|---|---|---|---|---|---|---|---|---|
|202504|youtube|60171|27.544|64.487|68.214|35.385|35.905|36.554|
|202504|instagram|53247|97.752|98.887|99.718|93.235|92.773|93.198|
|202504|tiktok|11933|91.676|96.168|95.738|65.408|63.894|65.105|
|202504|snapchat|57813|77.861|90.136|93.154|65.820|65.321|66.261|
|202504|spotify|17181|51.129|83.913|89.623|56.957|57.551|57.175|
|202504|discord|5770|63.189|94.172|73.805|62.439|62.707|62.259|
|202504|google-www|22292|19.533|39.439|47.688|6.088|6.925|6.568|
|202504|google-play|12556|21.016|43.792|54.536|31.293|30.364|31.076|
|202504|google-services|16790|36.781|50.137|60.743|23.876|24.926|24.805|
|202504|google-gstatic|16310|41.699|49.413|54.283|44.613|44.303|44.608|
|202504|google-usercontent|19125|24.146|55.605|58.688|37.448|37.049|36.436|
|202504|google-authentication|7616|14.311|41.301|45.435|24.087|24.051|24.611|
|202504|google-fonts|7884|22.563|23.336|26.278|17.885|18.302|18.225|
|202504|google-drive|511|3.473|6.189|8.089|4.629|4.110|4.620|
|202504|google-docs|973|6.313|15.565|19.298|8.237|7.670|8.618|
|202504|google-translate|518|1.614|5.173|5.232|4.105|3.901|3.844|
|202504|google-ads|41712|32.399|41.428|47.602|18.671|18.097|19.176|
|202504|google-safebrowsing|1657|13.867|40.660|48.203|8.531|8.855|8.825|
|202504|google-imasdk|551|2.479|3.543|5.988|1.623|1.551|1.524|
|202504|google-calendar|24584|32.162|63.293|73.112|39.525|40.759|41.373|
|202505|youtube|61631|27.422|64.731|68.371|36.083|36.669|37.397|
|202505|instagram|45256|97.346|98.801|99.587|91.639|90.942|91.333|
|202505|tiktok|13193|96.440|96.779|97.201|70.337|69.226|70.043|
|202505|snapchat|53748|78.036|90.328|93.305|66.722|66.285|67.168|
|202505|spotify|16916|51.492|84.354|89.969|58.066|58.784|58.355|
|202505|discord|6035|65.547|94.774|75.968|65.446|65.537|64.788|
|202505|google-www|22661|20.143|40.171|47.797|6.563|7.503|7.198|
|202505|google-play|12307|20.580|41.910|52.092|29.723|28.682|29.475|
|202505|google-services|16838|37.086|50.010|61.038|24.773|25.641|25.756|
|202505|google-gstatic|15724|42.123|48.590|54.539|43.338|42.940|43.255|
|202505|google-usercontent|18222|23.343|54.783|58.817|36.172|35.870|35.336|
|202505|google-authentication|6976|13.029|41.217|43.949|24.100|23.858|24.647|
|202505|google-fonts|7762|21.998|23.272|26.401|17.978|18.100|18.010|
|202505|google-drive|504|3.351|5.647|7.591|4.145|3.770|4.217|
|202505|google-docs|879|6.157|14.775|19.427|7.064|6.701|7.383|
|202505|google-translate|466|1.577|4.489|4.761|4.289|3.982|3.869|
|202505|google-ads|39760|32.027|40.815|46.288|18.921|18.267|19.357|
|202505|google-safebrowsing|1587|12.838|39.155|46.695|8.707|9.031|9.018|
|202505|google-imasdk|640|2.626|3.950|6.034|1.794|1.716|1.652|
|202505|google-calendar|24153|31.803|64.411|73.777|39.684|40.810|41.545|

같은평가플로우에대한5개모델혼동행렬합계이며서로다른플로우5배가아니다. 행=정답,열=예측.

|월|모델|정답→예측|5반복오분류합|
|---|---|---|---|
|202504|M2|youtube→google-ads|23620|
|202504|M2|google-ads→google-fonts|20897|
|202504|M2|google-ads→google-www|20313|
|202504|M2|google-usercontent→google-calendar|17759|
|202504|M2|youtube→google-fonts|17265|
|202504|M5|youtube→google-usercontent|36337|
|202504|M5|snapchat→spotify|36275|
|202504|M5|google-usercontent→google-calendar|30259|
|202504|M5|youtube→google-ads|28930|
|202504|M5|google-ads→spotify|23997|
|202505|M2|youtube→google-ads|25067|
|202505|M2|google-ads→google-fonts|20695|
|202505|M2|google-ads→google-www|19578|
|202505|M2|youtube→google-www|17263|
|202505|M2|google-usercontent→google-calendar|17139|
|202505|M5|youtube→google-usercontent|37216|
|202505|M5|snapchat→spotify|34791|
|202505|M5|google-usercontent→google-calendar|29443|
|202505|M5|youtube→google-ads|28799|
|202505|M5|google-ads→google-calendar|21974|


</details>
<details><summary>mixed_n50 전체·겹침·비겹침·공통미관측</summary>


|월|부분집합|모델|N범위|support있는클래스범위|F1평균±SD(%)|정확도평균±SD(%)|
|---|---|---|---|---|---|---|
|202504|all|M0|379194–379194|20–20|29.233 ± 0.982|41.663 ± 1.707|
|202504|all|M1|379194–379194|20–20|40.651 ± 1.032|53.801 ± 1.575|
|202504|all|M2|379194–379194|20–20|42.319 ± 1.691|58.263 ± 2.621|
|202504|all|M3|379194–379194|20–20|19.088 ± 0.886|27.396 ± 1.807|
|202504|all|M4|379194–379194|20–20|18.909 ± 0.866|27.177 ± 1.547|
|202504|all|M5|379194–379194|20–20|19.475 ± 0.902|28.808 ± 1.691|
|202504|train_overlap|M0|0–2|0–1|N/A|N/A|
|202504|train_overlap|M1|0–2|0–1|N/A|N/A|
|202504|train_overlap|M2|0–2|0–1|N/A|N/A|
|202504|train_overlap|M3|0–2|0–1|N/A|N/A|
|202504|train_overlap|M4|0–2|0–1|N/A|N/A|
|202504|train_overlap|M5|0–2|0–1|N/A|N/A|
|202504|train_nonoverlap|M0|379192–379194|20–20|29.233 ± 0.982|41.663 ± 1.707|
|202504|train_nonoverlap|M1|379192–379194|20–20|40.651 ± 1.032|53.801 ± 1.575|
|202504|train_nonoverlap|M2|379192–379194|20–20|42.319 ± 1.691|58.263 ± 2.621|
|202504|train_nonoverlap|M3|379192–379194|20–20|19.088 ± 0.886|27.397 ± 1.807|
|202504|train_nonoverlap|M4|379192–379194|20–20|18.909 ± 0.866|27.177 ± 1.547|
|202504|train_nonoverlap|M5|379192–379194|20–20|19.475 ± 0.902|28.808 ± 1.690|
|202504|common_unseen|M0|376465–376465|20–20|29.357 ± 0.993|41.923 ± 1.714|
|202504|common_unseen|M1|376465–376465|20–20|40.778 ± 1.031|54.163 ± 1.568|
|202504|common_unseen|M2|376465–376465|20–20|42.514 ± 1.720|58.658 ± 2.629|
|202504|common_unseen|M3|376465–376465|20–20|19.162 ± 0.896|27.574 ± 1.814|
|202504|common_unseen|M4|376465–376465|20–20|18.977 ± 0.866|27.357 ± 1.561|
|202504|common_unseen|M5|376465–376465|20–20|19.578 ± 0.911|28.992 ± 1.689|
|202505|all|M0|365258–365258|20–20|29.513 ± 0.939|40.802 ± 1.756|
|202505|all|M1|365258–365258|20–20|40.766 ± 0.831|53.196 ± 1.579|
|202505|all|M2|365258–365258|20–20|42.151 ± 1.540|57.512 ± 2.351|
|202505|all|M3|365258–365258|20–20|19.299 ± 0.876|26.911 ± 1.626|
|202505|all|M4|365258–365258|20–20|19.133 ± 0.858|26.713 ± 1.427|
|202505|all|M5|365258–365258|20–20|19.689 ± 0.914|28.144 ± 1.618|
|202505|train_overlap|M0|0–6|0–2|N/A|N/A|
|202505|train_overlap|M1|0–6|0–2|N/A|N/A|
|202505|train_overlap|M2|0–6|0–2|N/A|N/A|
|202505|train_overlap|M3|0–6|0–2|N/A|N/A|
|202505|train_overlap|M4|0–6|0–2|N/A|N/A|
|202505|train_overlap|M5|0–6|0–2|N/A|N/A|
|202505|train_nonoverlap|M0|365252–365258|20–20|29.513 ± 0.939|40.802 ± 1.756|
|202505|train_nonoverlap|M1|365252–365258|20–20|40.766 ± 0.831|53.196 ± 1.579|
|202505|train_nonoverlap|M2|365252–365258|20–20|42.151 ± 1.540|57.512 ± 2.351|
|202505|train_nonoverlap|M3|365252–365258|20–20|19.299 ± 0.876|26.911 ± 1.626|
|202505|train_nonoverlap|M4|365252–365258|20–20|19.132 ± 0.858|26.713 ± 1.427|
|202505|train_nonoverlap|M5|365252–365258|20–20|19.689 ± 0.914|28.144 ± 1.618|
|202505|common_unseen|M0|362640–362640|20–20|29.629 ± 0.946|41.027 ± 1.761|
|202505|common_unseen|M1|362640–362640|20–20|40.906 ± 0.831|53.551 ± 1.572|
|202505|common_unseen|M2|362640–362640|20–20|42.341 ± 1.550|57.883 ± 2.353|
|202505|common_unseen|M3|362640–362640|20–20|19.379 ± 0.888|27.087 ± 1.632|
|202505|common_unseen|M4|362640–362640|20–20|19.208 ± 0.861|26.891 ± 1.439|
|202505|common_unseen|M5|362640–362640|20–20|19.801 ± 0.926|28.327 ± 1.618|

빈부분집합은N/A. 고정클래스수에서support없는클래스처리규칙을유지한다. 희소겹침집단은전체서비스성능추정이아니다.

</details>
<details><summary>mixed_n50 서비스별F1과교사·학생의주요혼동</summary>


|월|서비스|support|M0|M1|M2|M3|M4|M5|
|---|---|---|---|---|---|---|---|---|
|202504|youtube|60171|23.437|45.758|55.350|19.833|18.967|17.408|
|202504|instagram|53247|94.120|97.290|97.922|64.626|64.446|70.456|
|202504|tiktok|11933|91.655|90.849|92.476|45.920|45.779|45.007|
|202504|snapchat|57813|69.160|78.218|86.379|27.930|25.657|29.032|
|202504|spotify|17181|39.424|73.726|79.771|31.448|31.379|31.605|
|202504|discord|5770|46.344|83.909|67.379|28.391|26.888|29.255|
|202504|google-www|22292|15.567|22.262|28.453|1.676|1.972|1.346|
|202504|google-play|12556|15.450|25.544|22.302|21.445|21.513|20.568|
|202504|google-services|16790|24.359|28.268|27.317|3.015|2.991|2.969|
|202504|google-gstatic|16310|33.734|46.548|43.864|34.325|34.458|36.351|
|202504|google-usercontent|19125|22.003|50.960|51.628|26.730|26.752|27.032|
|202504|google-authentication|7616|12.874|28.949|35.256|13.231|14.064|14.166|
|202504|google-fonts|7884|16.962|17.931|19.189|6.773|7.376|7.584|
|202504|google-drive|511|2.462|3.416|3.612|2.320|2.341|2.410|
|202504|google-docs|973|4.574|7.313|8.810|1.901|1.726|1.826|
|202504|google-translate|518|1.123|2.666|3.184|2.347|2.572|2.634|
|202504|google-ads|41712|26.172|29.697|32.369|9.405|9.051|8.669|
|202504|google-safebrowsing|1657|10.378|23.668|24.911|5.201|5.147|5.074|
|202504|google-imasdk|551|1.889|1.344|2.319|1.306|1.220|1.332|
|202504|google-calendar|24584|32.967|54.711|63.882|33.937|33.872|34.771|
|202505|youtube|61631|23.793|46.619|55.722|20.950|20.119|18.479|
|202505|instagram|45256|93.181|96.953|97.276|61.941|61.826|67.549|
|202505|tiktok|13193|96.458|92.584|95.647|51.204|51.153|50.589|
|202505|snapchat|53748|69.637|78.935|86.943|28.536|26.104|29.283|
|202505|spotify|16916|39.288|74.105|80.310|31.835|31.750|32.118|
|202505|discord|6035|49.246|85.729|68.203|30.673|29.140|31.200|
|202505|google-www|22661|16.076|23.036|28.493|1.949|2.250|1.524|
|202505|google-play|12307|15.492|24.987|21.642|20.021|20.054|19.465|
|202505|google-services|16838|23.908|28.832|26.674|2.957|2.859|2.843|
|202505|google-gstatic|15724|34.115|45.612|42.264|33.430|33.610|35.495|
|202505|google-usercontent|18222|21.496|50.317|50.124|25.799|25.833|26.016|
|202505|google-authentication|6976|11.869|28.469|32.953|13.429|14.348|14.463|
|202505|google-fonts|7762|17.040|17.630|19.006|7.105|7.814|8.018|
|202505|google-drive|504|2.497|3.135|3.551|2.171|2.209|2.098|
|202505|google-docs|879|4.534|7.066|8.351|1.446|1.390|1.749|
|202505|google-translate|466|1.040|2.500|3.017|2.557|2.757|2.746|
|202505|google-ads|39760|25.698|29.282|31.441|9.557|9.182|8.844|
|202505|google-safebrowsing|1587|10.015|23.403|24.401|5.427|5.367|5.318|
|202505|google-imasdk|640|2.179|1.532|2.335|1.284|1.210|1.312|
|202505|google-calendar|24153|32.690|54.603|64.673|33.709|33.674|34.676|

같은평가플로우에대한5개모델혼동행렬합계이며서로다른플로우5배가아니다. 행=정답,열=예측.

|월|모델|정답→예측|5반복오분류합|
|---|---|---|---|
|202504|M2|google-ads→google-gstatic|24962|
|202504|M2|google-usercontent→google-calendar|23223|
|202504|M2|youtube→google-usercontent|20577|
|202504|M2|youtube→google-fonts|19620|
|202504|M2|google-ads→google-fonts|19532|
|202504|M5|youtube→google-calendar|81635|
|202504|M5|snapchat→spotify|74856|
|202504|M5|google-ads→google-calendar|48703|
|202504|M5|google-usercontent→google-calendar|43136|
|202504|M5|youtube→google-usercontent|41978|
|202505|M2|google-ads→google-gstatic|23878|
|202505|M2|youtube→google-usercontent|22113|
|202505|M2|google-usercontent→google-calendar|22108|
|202505|M2|google-ads→google-fonts|19188|
|202505|M2|google-ads→google-www|17724|
|202505|M5|youtube→google-calendar|84257|
|202505|M5|snapchat→spotify|71992|
|202505|M5|google-ads→google-calendar|46843|
|202505|M5|youtube→google-usercontent|43443|
|202505|M5|google-usercontent→google-calendar|41188|


</details>
<details><summary>mixed_n100 전체·겹침·비겹침·공통미관측</summary>


|월|부분집합|모델|N범위|support있는클래스범위|F1평균±SD(%)|정확도평균±SD(%)|
|---|---|---|---|---|---|---|
|202504|all|M0|379194–379194|20–20|31.830 ± 0.691|44.696 ± 0.650|
|202504|all|M1|379194–379194|20–20|46.675 ± 0.322|60.660 ± 0.466|
|202504|all|M2|379194–379194|20–20|49.310 ± 1.721|64.939 ± 1.576|
|202504|all|M3|379194–379194|20–20|26.140 ± 0.819|37.716 ± 1.206|
|202504|all|M4|379194–379194|20–20|26.310 ± 0.837|38.176 ± 1.370|
|202504|all|M5|379194–379194|20–20|26.463 ± 0.921|37.765 ± 1.897|
|202504|train_overlap|M0|0–5|0–2|N/A|N/A|
|202504|train_overlap|M1|0–5|0–2|N/A|N/A|
|202504|train_overlap|M2|0–5|0–2|N/A|N/A|
|202504|train_overlap|M3|0–5|0–2|N/A|N/A|
|202504|train_overlap|M4|0–5|0–2|N/A|N/A|
|202504|train_overlap|M5|0–5|0–2|N/A|N/A|
|202504|train_nonoverlap|M0|379189–379194|20–20|31.830 ± 0.691|44.696 ± 0.650|
|202504|train_nonoverlap|M1|379189–379194|20–20|46.675 ± 0.322|60.660 ± 0.466|
|202504|train_nonoverlap|M2|379189–379194|20–20|49.310 ± 1.721|64.939 ± 1.576|
|202504|train_nonoverlap|M3|379189–379194|20–20|26.140 ± 0.819|37.716 ± 1.206|
|202504|train_nonoverlap|M4|379189–379194|20–20|26.310 ± 0.837|38.176 ± 1.370|
|202504|train_nonoverlap|M5|379189–379194|20–20|26.463 ± 0.921|37.765 ± 1.897|
|202504|common_unseen|M0|376465–376465|20–20|31.935 ± 0.716|44.904 ± 0.643|
|202504|common_unseen|M1|376465–376465|20–20|46.902 ± 0.433|61.013 ± 0.478|
|202504|common_unseen|M2|376465–376465|20–20|49.547 ± 1.735|65.339 ± 1.566|
|202504|common_unseen|M3|376465–376465|20–20|26.280 ± 0.788|37.972 ± 1.223|
|202504|common_unseen|M4|376465–376465|20–20|26.459 ± 0.817|38.427 ± 1.382|
|202504|common_unseen|M5|376465–376465|20–20|26.605 ± 0.881|38.022 ± 1.925|
|202505|all|M0|365258–365258|20–20|32.049 ± 0.617|43.780 ± 0.604|
|202505|all|M1|365258–365258|20–20|46.533 ± 0.294|59.991 ± 0.432|
|202505|all|M2|365258–365258|20–20|49.379 ± 1.473|64.541 ± 1.284|
|202505|all|M3|365258–365258|20–20|26.386 ± 0.829|36.961 ± 1.059|
|202505|all|M4|365258–365258|20–20|26.578 ± 0.832|37.458 ± 1.223|
|202505|all|M5|365258–365258|20–20|26.697 ± 0.895|37.000 ± 1.786|
|202505|train_overlap|M0|0–6|0–2|N/A|N/A|
|202505|train_overlap|M1|0–6|0–2|N/A|N/A|
|202505|train_overlap|M2|0–6|0–2|N/A|N/A|
|202505|train_overlap|M3|0–6|0–2|N/A|N/A|
|202505|train_overlap|M4|0–6|0–2|N/A|N/A|
|202505|train_overlap|M5|0–6|0–2|N/A|N/A|
|202505|train_nonoverlap|M0|365252–365258|20–20|32.049 ± 0.617|43.780 ± 0.604|
|202505|train_nonoverlap|M1|365252–365258|20–20|46.533 ± 0.293|59.992 ± 0.432|
|202505|train_nonoverlap|M2|365252–365258|20–20|49.379 ± 1.473|64.541 ± 1.284|
|202505|train_nonoverlap|M3|365252–365258|20–20|26.386 ± 0.829|36.961 ± 1.059|
|202505|train_nonoverlap|M4|365252–365258|20–20|26.578 ± 0.832|37.458 ± 1.223|
|202505|train_nonoverlap|M5|365252–365258|20–20|26.697 ± 0.895|37.000 ± 1.786|
|202505|common_unseen|M0|362640–362640|20–20|32.144 ± 0.641|43.949 ± 0.611|
|202505|common_unseen|M1|362640–362640|20–20|46.767 ± 0.386|60.329 ± 0.436|
|202505|common_unseen|M2|362640–362640|20–20|49.600 ± 1.497|64.908 ± 1.286|
|202505|common_unseen|M3|362640–362640|20–20|26.537 ± 0.798|37.212 ± 1.072|
|202505|common_unseen|M4|362640–362640|20–20|26.733 ± 0.812|37.699 ± 1.235|
|202505|common_unseen|M5|362640–362640|20–20|26.849 ± 0.852|37.252 ± 1.811|

빈부분집합은N/A. 고정클래스수에서support없는클래스처리규칙을유지한다. 희소겹침집단은전체서비스성능추정이아니다.

</details>
<details><summary>mixed_n100 서비스별F1과교사·학생의주요혼동</summary>


|월|서비스|support|M0|M1|M2|M3|M4|M5|
|---|---|---|---|---|---|---|---|---|
|202504|youtube|60171|24.533|58.768|63.269|28.453|30.669|27.453|
|202504|instagram|53247|96.748|98.978|99.585|84.488|84.818|83.860|
|202504|tiktok|11933|91.742|93.732|93.427|55.500|55.955|56.321|
|202504|snapchat|57813|74.192|85.576|90.204|48.822|49.807|49.817|
|202504|spotify|17181|47.294|79.295|85.149|46.875|46.637|46.817|
|202504|discord|5770|55.115|93.653|73.855|43.873|44.119|44.205|
|202504|google-www|22292|17.362|34.212|39.217|3.510|3.633|3.488|
|202504|google-play|12556|18.183|33.955|43.593|27.704|27.326|28.227|
|202504|google-services|16790|31.622|39.864|49.345|10.619|11.453|12.554|
|202504|google-gstatic|16310|38.324|50.502|49.742|41.186|41.476|41.850|
|202504|google-usercontent|19125|22.471|57.169|55.934|31.178|30.764|31.069|
|202504|google-authentication|7616|13.365|36.124|40.926|19.400|19.031|20.949|
|202504|google-fonts|7884|20.143|20.808|22.833|10.932|11.095|11.759|
|202504|google-drive|511|2.617|4.265|6.882|3.262|3.095|2.926|
|202504|google-docs|973|6.068|11.371|17.562|5.702|5.890|5.426|
|202504|google-translate|518|1.325|3.586|4.274|3.886|3.818|3.915|
|202504|google-ads|41712|28.269|35.349|40.362|12.061|11.818|12.511|
|202504|google-safebrowsing|1657|11.945|29.573|37.221|5.962|6.048|6.095|
|202504|google-imasdk|551|1.971|2.596|3.850|1.511|1.569|1.480|
|202504|google-calendar|24584|33.305|64.119|68.981|37.877|37.181|38.540|
|202505|youtube|61631|24.440|59.283|63.530|29.553|31.637|28.269|
|202505|instagram|45256|96.303|98.820|99.363|82.149|82.597|81.500|
|202505|tiktok|13193|96.449|94.501|96.285|60.926|61.671|61.896|
|202505|snapchat|53748|74.333|86.032|90.665|49.445|50.420|50.497|
|202505|spotify|16916|47.794|79.503|85.771|47.745|47.580|47.678|
|202505|discord|6035|57.744|93.833|74.740|46.514|46.877|46.754|
|202505|google-www|22661|18.014|34.683|39.753|3.784|4.007|3.816|
|202505|google-play|12307|17.984|32.622|41.702|26.009|25.852|26.486|
|202505|google-services|16838|31.259|39.433|49.362|10.561|11.563|12.646|
|202505|google-gstatic|15724|38.508|49.586|49.003|40.062|40.352|40.660|
|202505|google-usercontent|18222|21.885|56.134|55.751|30.394|29.932|30.575|
|202505|google-authentication|6976|12.362|35.665|39.822|19.853|19.422|21.287|
|202505|google-fonts|7762|19.646|20.559|22.995|11.125|10.906|11.887|
|202505|google-drive|504|2.512|4.127|6.418|3.240|3.052|2.864|
|202505|google-docs|879|6.173|11.089|17.835|5.037|5.086|4.506|
|202505|google-translate|466|1.288|3.333|3.943|4.071|4.155|4.015|
|202505|google-ads|39760|27.671|35.078|39.858|12.153|11.826|12.659|
|202505|google-safebrowsing|1587|11.264|29.366|36.642|6.110|6.099|6.314|
|202505|google-imasdk|640|2.241|2.874|3.847|1.557|1.629|1.508|
|202505|google-calendar|24153|33.108|64.136|70.297|37.422|36.898|38.114|

같은평가플로우에대한5개모델혼동행렬합계이며서로다른플로우5배가아니다. 행=정답,열=예측.

|월|모델|정답→예측|5반복오분류합|
|---|---|---|---|
|202504|M2|google-ads→google-fonts|23281|
|202504|M2|google-ads→google-gstatic|22191|
|202504|M2|google-usercontent→google-calendar|20446|
|202504|M2|google-ads→google-www|20240|
|202504|M2|youtube→google-fonts|18737|
|202504|M5|youtube→google-calendar|53617|
|202504|M5|snapchat→spotify|48022|
|202504|M5|google-ads→google-calendar|42888|
|202504|M5|youtube→google-usercontent|41292|
|202504|M5|google-usercontent→google-calendar|35738|
|202505|M2|google-ads→google-fonts|23079|
|202505|M2|google-ads→google-gstatic|21163|
|202505|M2|google-usercontent→google-calendar|19570|
|202505|M2|google-ads→google-www|19294|
|202505|M2|youtube→google-www|16654|
|202505|M5|youtube→google-calendar|56555|
|202505|M5|snapchat→spotify|45972|
|202505|M5|youtube→google-usercontent|42009|
|202505|M5|google-ads→google-calendar|41881|
|202505|M5|google-usercontent→google-calendar|34427|


</details>
<details><summary>mixed_n1000 전체·겹침·비겹침·공통미관측</summary>


|월|부분집합|모델|N범위|support있는클래스범위|F1평균±SD(%)|정확도평균±SD(%)|
|---|---|---|---|---|---|---|
|202504|all|M0|379194–379194|20–20|38.623 ± 0.334|52.220 ± 0.301|
|202504|all|M1|379194–379194|20–20|58.396 ± 1.181|72.793 ± 1.941|
|202504|all|M2|379194–379194|20–20|62.475 ± 0.820|77.168 ± 0.693|
|202504|all|M3|379194–379194|20–20|46.098 ± 0.243|60.954 ± 0.288|
|202504|all|M4|379194–379194|20–20|46.423 ± 0.489|61.096 ± 0.636|
|202504|all|M5|379194–379194|20–20|46.342 ± 0.599|61.122 ± 0.729|
|202504|train_overlap|M0|16–56|6–9|20.357 ± 3.337|55.862 ± 19.550|
|202504|train_overlap|M1|16–56|6–9|19.324 ± 6.396|46.612 ± 24.782|
|202504|train_overlap|M2|16–56|6–9|20.957 ± 4.568|57.518 ± 18.677|
|202504|train_overlap|M3|16–56|6–9|16.257 ± 1.943|41.849 ± 13.709|
|202504|train_overlap|M4|16–56|6–9|15.224 ± 2.464|42.123 ± 13.389|
|202504|train_overlap|M5|16–56|6–9|19.000 ± 4.704|53.254 ± 20.961|
|202504|train_nonoverlap|M0|379138–379178|20–20|38.622 ± 0.335|52.220 ± 0.302|
|202504|train_nonoverlap|M1|379138–379178|20–20|58.398 ± 1.181|72.795 ± 1.941|
|202504|train_nonoverlap|M2|379138–379178|20–20|62.477 ± 0.820|77.169 ± 0.692|
|202504|train_nonoverlap|M3|379138–379178|20–20|46.099 ± 0.243|60.956 ± 0.288|
|202504|train_nonoverlap|M4|379138–379178|20–20|46.424 ± 0.491|61.098 ± 0.637|
|202504|train_nonoverlap|M5|379138–379178|20–20|46.342 ± 0.599|61.122 ± 0.729|
|202504|common_unseen|M0|376465–376465|20–20|38.765 ± 0.339|52.524 ± 0.293|
|202504|common_unseen|M1|376465–376465|20–20|58.706 ± 1.153|73.232 ± 1.984|
|202504|common_unseen|M2|376465–376465|20–20|62.667 ± 0.918|77.411 ± 0.807|
|202504|common_unseen|M3|376465–376465|20–20|46.216 ± 0.265|61.193 ± 0.428|
|202504|common_unseen|M4|376465–376465|20–20|46.529 ± 0.501|61.310 ± 0.705|
|202504|common_unseen|M5|376465–376465|20–20|46.472 ± 0.590|61.423 ± 0.701|
|202505|all|M0|365258–365258|20–20|38.761 ± 0.352|51.277 ± 0.304|
|202505|all|M1|365258–365258|20–20|57.836 ± 1.042|72.102 ± 1.625|
|202505|all|M2|365258–365258|20–20|62.159 ± 0.693|76.722 ± 0.612|
|202505|all|M3|365258–365258|20–20|45.893 ± 0.236|60.159 ± 0.222|
|202505|all|M4|365258–365258|20–20|46.194 ± 0.571|60.275 ± 0.619|
|202505|all|M5|365258–365258|20–20|46.176 ± 0.645|60.323 ± 0.762|
|202505|train_overlap|M0|19–160|7–9|15.610 ± 4.192|49.242 ± 26.148|
|202505|train_overlap|M1|19–160|7–9|14.752 ± 5.623|40.366 ± 30.461|
|202505|train_overlap|M2|19–160|7–9|16.410 ± 3.314|53.687 ± 21.960|
|202505|train_overlap|M3|19–160|7–9|13.069 ± 4.591|37.315 ± 17.009|
|202505|train_overlap|M4|19–160|7–9|13.590 ± 2.065|35.768 ± 15.041|
|202505|train_overlap|M5|19–160|7–9|15.600 ± 1.949|52.821 ± 22.145|
|202505|train_nonoverlap|M0|365098–365239|20–20|38.760 ± 0.352|51.274 ± 0.306|
|202505|train_nonoverlap|M1|365098–365239|20–20|57.838 ± 1.041|72.104 ± 1.623|
|202505|train_nonoverlap|M2|365098–365239|20–20|62.161 ± 0.693|76.722 ± 0.612|
|202505|train_nonoverlap|M3|365098–365239|20–20|45.900 ± 0.231|60.164 ± 0.226|
|202505|train_nonoverlap|M4|365098–365239|20–20|46.200 ± 0.576|60.280 ± 0.625|
|202505|train_nonoverlap|M5|365098–365239|20–20|46.176 ± 0.644|60.322 ± 0.759|
|202505|common_unseen|M0|362640–362640|20–20|38.891 ± 0.353|51.546 ± 0.298|
|202505|common_unseen|M1|362640–362640|20–20|58.123 ± 1.016|72.504 ± 1.677|
|202505|common_unseen|M2|362640–362640|20–20|62.340 ± 0.781|76.932 ± 0.726|
|202505|common_unseen|M3|362640–362640|20–20|46.003 ± 0.229|60.363 ± 0.352|
|202505|common_unseen|M4|362640–362640|20–20|46.299 ± 0.587|60.465 ± 0.680|
|202505|common_unseen|M5|362640–362640|20–20|46.294 ± 0.630|60.584 ± 0.729|

빈부분집합은N/A. 고정클래스수에서support없는클래스처리규칙을유지한다. 희소겹침집단은전체서비스성능추정이아니다.

</details>
<details><summary>mixed_n1000 서비스별F1과교사·학생의주요혼동</summary>


|월|서비스|support|M0|M1|M2|M3|M4|M5|
|---|---|---|---|---|---|---|---|---|
|202504|youtube|60171|33.796|70.463|74.465|56.532|56.380|55.870|
|202504|instagram|53247|99.331|99.642|99.896|97.414|97.364|97.506|
|202504|tiktok|11933|91.725|98.443|98.474|91.186|90.986|91.732|
|202504|snapchat|57813|84.500|95.656|97.707|83.706|83.977|83.434|
|202504|spotify|17181|57.756|92.793|95.607|79.724|79.748|80.074|
|202504|discord|5770|77.395|95.857|88.809|84.878|85.155|85.976|
|202504|google-www|22292|24.675|51.222|58.872|24.562|25.239|24.719|
|202504|google-play|12556|29.822|62.556|69.630|39.178|38.117|38.532|
|202504|google-services|16790|43.851|66.752|71.842|40.109|40.661|38.421|
|202504|google-gstatic|16310|46.458|58.534|63.965|49.352|49.888|50.844|
|202504|google-usercontent|19125|30.323|63.123|73.390|52.557|58.075|55.333|
|202504|google-authentication|7616|16.144|55.397|60.321|38.440|38.234|38.558|
|202504|google-fonts|7884|27.206|38.824|39.955|27.043|27.516|27.537|
|202504|google-drive|511|5.495|8.526|13.428|6.486|6.290|6.788|
|202504|google-docs|973|9.702|21.204|25.258|13.678|14.190|12.994|
|202504|google-translate|518|2.419|9.501|9.131|4.604|5.016|4.759|
|202504|google-ads|41712|39.815|47.586|56.815|40.293|39.973|40.694|
|202504|google-safebrowsing|1657|17.651|51.111|67.081|21.391|20.708|22.823|
|202504|google-imasdk|551|2.958|6.696|8.850|2.852|2.959|2.859|
|202504|google-calendar|24584|31.438|74.046|76.010|67.973|67.975|67.391|
|202505|youtube|61631|33.112|71.209|74.508|56.725|56.509|55.755|
|202505|instagram|45256|99.196|99.608|99.873|96.686|96.694|96.824|
|202505|tiktok|13193|96.523|98.907|99.033|91.885|91.737|92.656|
|202505|snapchat|53748|84.365|95.560|97.788|84.434|84.546|84.098|
|202505|spotify|16916|58.593|92.780|95.876|80.305|80.361|80.890|
|202505|discord|6035|79.154|96.210|89.746|86.578|86.932|87.519|
|202505|google-www|22661|25.216|50.666|59.494|26.084|26.280|25.910|
|202505|google-play|12307|29.204|59.380|67.010|37.297|36.073|36.585|
|202505|google-services|16838|45.127|64.887|72.547|40.288|41.233|38.608|
|202505|google-gstatic|15724|47.303|58.516|65.294|48.210|48.416|49.833|
|202505|google-usercontent|18222|29.585|62.216|72.267|51.083|56.319|53.944|
|202505|google-authentication|6976|14.768|54.723|59.425|37.297|36.765|37.345|
|202505|google-fonts|7762|27.017|39.187|40.324|27.029|27.246|27.571|
|202505|google-drive|504|4.779|7.815|12.607|5.974|6.071|6.338|
|202505|google-docs|879|9.047|18.955|24.800|11.877|12.924|11.775|
|202505|google-translate|466|2.179|8.225|8.220|4.161|4.641|4.382|
|202505|google-ads|39760|39.464|46.400|55.183|40.075|39.825|40.614|
|202505|google-safebrowsing|1587|16.445|48.747|62.234|20.963|20.163|22.443|
|202505|google-imasdk|640|2.933|7.222|9.077|3.234|3.396|3.343|
|202505|google-calendar|24153|31.207|75.505|77.876|67.669|67.743|67.096|

같은평가플로우에대한5개모델혼동행렬합계이며서로다른플로우5배가아니다. 행=정답,열=예측.

|월|모델|정답→예측|5반복오분류합|
|---|---|---|---|
|202504|M2|youtube→google-ads|26338|
|202504|M2|youtube→google-www|17802|
|202504|M2|google-ads→youtube|17738|
|202504|M2|google-ads→google-www|17290|
|202504|M2|google-ads→google-fonts|13993|
|202504|M5|google-ads→google-fonts|25975|
|202504|M5|google-usercontent→google-calendar|22004|
|202504|M5|youtube→google-fonts|20860|
|202504|M5|snapchat→spotify|20857|
|202504|M5|youtube→google-authentication|20258|
|202505|M2|youtube→google-ads|28592|
|202505|M2|youtube→google-www|20205|
|202505|M2|google-ads→google-www|17271|
|202505|M2|google-ads→youtube|16784|
|202505|M2|google-ads→google-fonts|14272|
|202505|M5|google-ads→google-fonts|24880|
|202505|M5|youtube→google-authentication|22547|
|202505|M5|google-usercontent→google-calendar|21488|
|202505|M5|youtube→google-fonts|19950|
|202505|M5|snapchat→spotify|19478|


</details>
<details><summary>nongoogle_n200 전체·겹침·비겹침·공통미관측</summary>


|월|부분집합|모델|N범위|support있는클래스범위|F1평균±SD(%)|정확도평균±SD(%)|
|---|---|---|---|---|---|---|
|202504|all|M0|252471–252471|13–13|62.369 ± 0.503|74.331 ± 0.701|
|202504|all|M1|252471–252471|13–13|78.208 ± 1.273|87.219 ± 0.620|
|202504|all|M2|252471–252471|13–13|80.171 ± 1.549|88.886 ± 1.140|
|202504|all|M3|252471–252471|13–13|47.855 ± 2.517|56.871 ± 2.443|
|202504|all|M4|252471–252471|13–13|47.899 ± 2.399|57.160 ± 2.130|
|202504|all|M5|252471–252471|13–13|48.194 ± 1.684|57.228 ± 1.043|
|202504|train_overlap|M0|6–28|3–4|18.901 ± 3.916|82.026 ± 10.501|
|202504|train_overlap|M1|6–28|3–4|18.901 ± 3.916|82.026 ± 10.501|
|202504|train_overlap|M2|6–28|3–4|18.462 ± 4.213|81.117 ± 11.190|
|202504|train_overlap|M3|6–28|3–4|15.175 ± 0.469|73.165 ± 9.660|
|202504|train_overlap|M4|6–28|3–4|14.021 ± 3.049|73.165 ± 9.660|
|202504|train_overlap|M5|6–28|3–4|15.385 ± 0.000|77.450 ± 12.906|
|202504|train_nonoverlap|M0|252443–252465|13–13|62.367 ± 0.503|74.331 ± 0.701|
|202504|train_nonoverlap|M1|252443–252465|13–13|78.208 ± 1.273|87.219 ± 0.620|
|202504|train_nonoverlap|M2|252443–252465|13–13|80.172 ± 1.550|88.887 ± 1.141|
|202504|train_nonoverlap|M3|252443–252465|13–13|47.854 ± 2.517|56.870 ± 2.443|
|202504|train_nonoverlap|M4|252443–252465|13–13|47.897 ± 2.399|57.159 ± 2.130|
|202504|train_nonoverlap|M5|252443–252465|13–13|48.192 ± 1.684|57.227 ± 1.043|
|202504|common_unseen|M0|251691–251691|13–13|62.474 ± 0.499|74.378 ± 0.702|
|202504|common_unseen|M1|251691–251691|13–13|78.420 ± 1.240|87.292 ± 0.611|
|202504|common_unseen|M2|251691–251691|13–13|80.384 ± 1.551|88.960 ± 1.123|
|202504|common_unseen|M3|251691–251691|13–13|47.902 ± 2.520|56.897 ± 2.438|
|202504|common_unseen|M4|251691–251691|13–13|47.949 ± 2.402|57.188 ± 2.122|
|202504|common_unseen|M5|251691–251691|13–13|48.242 ± 1.687|57.250 ± 1.033|
|202505|all|M0|225067–225067|13–13|62.934 ± 0.279|75.541 ± 0.377|
|202505|all|M1|225067–225067|13–13|76.652 ± 0.982|86.235 ± 0.474|
|202505|all|M2|225067–225067|13–13|79.062 ± 1.756|87.922 ± 1.212|
|202505|all|M3|225067–225067|13–13|48.137 ± 2.402|57.689 ± 2.384|
|202505|all|M4|225067–225067|13–13|48.217 ± 2.300|57.969 ± 2.039|
|202505|all|M5|225067–225067|13–13|48.453 ± 1.634|58.034 ± 1.018|
|202505|train_overlap|M0|5–31|3–3|13.846 ± 6.436|86.731 ± 8.531|
|202505|train_overlap|M1|5–31|3–3|13.846 ± 6.436|86.731 ± 8.531|
|202505|train_overlap|M2|5–31|3–3|13.846 ± 6.436|86.731 ± 8.531|
|202505|train_overlap|M3|5–31|3–3|12.280 ± 4.252|82.450 ± 2.949|
|202505|train_overlap|M4|5–31|3–3|12.280 ± 4.252|82.450 ± 2.949|
|202505|train_overlap|M5|5–31|3–3|12.308 ± 4.213|83.095 ± 4.274|
|202505|train_nonoverlap|M0|225036–225062|13–13|62.932 ± 0.281|75.540 ± 0.377|
|202505|train_nonoverlap|M1|225036–225062|13–13|76.652 ± 0.983|86.235 ± 0.475|
|202505|train_nonoverlap|M2|225036–225062|13–13|79.063 ± 1.756|87.922 ± 1.213|
|202505|train_nonoverlap|M3|225036–225062|13–13|48.136 ± 2.403|57.688 ± 2.384|
|202505|train_nonoverlap|M4|225036–225062|13–13|48.216 ± 2.300|57.967 ± 2.039|
|202505|train_nonoverlap|M5|225036–225062|13–13|48.451 ± 1.635|58.032 ± 1.017|
|202505|common_unseen|M0|223930–223930|13–13|63.041 ± 0.280|75.543 ± 0.378|
|202505|common_unseen|M1|223930–223930|13–13|76.995 ± 1.022|86.330 ± 0.498|
|202505|common_unseen|M2|223930–223930|13–13|79.285 ± 1.786|87.979 ± 1.203|
|202505|common_unseen|M3|223930–223930|13–13|48.214 ± 2.414|57.709 ± 2.378|
|202505|common_unseen|M4|223930–223930|13–13|48.299 ± 2.306|57.989 ± 2.024|
|202505|common_unseen|M5|223930–223930|13–13|48.533 ± 1.646|58.048 ± 1.004|

빈부분집합은N/A. 고정클래스수에서support없는클래스처리규칙을유지한다. 희소겹침집단은전체서비스성능추정이아니다.

</details>
<details><summary>nongoogle_n200 서비스별F1과교사·학생의주요혼동</summary>


|월|서비스|support|M0|M1|M2|M3|M4|M5|
|---|---|---|---|---|---|---|---|---|
|202504|snapchat|57813|89.616|96.719|97.149|74.342|74.641|74.564|
|202504|apple-privaterelay|17001|94.694|99.378|99.660|90.905|90.923|90.580|
|202504|facebook-graph|51424|69.669|84.111|87.372|40.185|41.641|41.231|
|202504|instagram|53247|76.252|88.454|90.583|65.839|66.362|65.518|
|202504|spotify|17181|67.189|86.377|88.785|40.375|40.793|41.845|
|202504|facebook-media|14312|56.330|70.676|74.681|49.689|50.773|50.655|
|202504|facebook-web|16175|58.281|70.762|72.423|51.746|51.331|52.301|
|202504|tiktok|11933|92.583|98.143|98.062|65.848|66.175|67.063|
|202504|discord|5770|76.522|98.015|96.358|63.305|59.900|62.072|
|202504|whatsapp|1563|16.252|54.975|36.478|6.856|6.754|7.140|
|202504|unitygames|4104|62.558|83.944|90.678|48.308|48.190|48.214|
|202504|openx|598|11.705|29.933|38.515|5.468|5.688|5.586|
|202504|facebook-connect|1350|39.151|55.213|71.476|19.251|19.512|19.754|
|202505|snapchat|53748|89.798|96.643|97.061|75.316|75.532|75.602|
|202505|apple-privaterelay|17680|97.304|99.192|99.597|91.467|91.454|91.259|
|202505|facebook-graph|40486|69.901|80.759|83.835|38.259|39.833|39.178|
|202505|instagram|45256|75.211|84.888|87.137|64.608|65.051|64.208|
|202505|spotify|16916|67.910|86.177|89.040|39.901|40.532|41.609|
|202505|facebook-media|11620|56.482|70.430|75.735|49.726|50.536|50.505|
|202505|facebook-web|13415|58.529|70.373|71.181|51.281|50.894|51.408|
|202505|tiktok|13193|97.144|97.540|98.742|70.873|71.225|71.862|
|202505|discord|6035|78.869|98.138|96.494|67.802|64.706|66.478|
|202505|whatsapp|1482|16.451|49.473|34.608|7.053|7.031|7.421|
|202505|unitygames|3489|60.073|82.185|88.935|45.108|45.131|45.300|
|202505|openx|568|12.486|28.037|38.555|5.495|5.687|5.635|
|202505|facebook-connect|1179|37.979|52.639|66.893|18.892|19.206|19.420|

같은평가플로우에대한5개모델혼동행렬합계이며서로다른플로우5배가아니다. 행=정답,열=예측.

|월|모델|정답→예측|5반복오분류합|
|---|---|---|---|
|202504|M2|facebook-graph→facebook-web|27990|
|202504|M2|instagram→facebook-media|11686|
|202504|M2|facebook-graph→whatsapp|9328|
|202504|M2|facebook-media→instagram|9013|
|202504|M2|snapchat→spotify|8111|
|202504|M5|facebook-graph→whatsapp|63275|
|202504|M5|facebook-graph→instagram|54354|
|202504|M5|instagram→facebook-graph|28463|
|202504|M5|facebook-graph→facebook-web|28338|
|202504|M5|snapchat→spotify|26088|
|202505|M2|facebook-graph→facebook-web|22444|
|202505|M2|instagram→facebook-media|11328|
|202505|M2|facebook-graph→whatsapp|10684|
|202505|M2|facebook-graph→instagram|9330|
|202505|M2|instagram→whatsapp|9000|
|202505|M5|facebook-graph→whatsapp|53632|
|202505|M5|facebook-graph→instagram|39535|
|202505|M5|instagram→facebook-graph|24740|
|202505|M5|spotify→unitygames|24721|
|202505|M5|snapchat→spotify|23319|


</details>
<details><summary>googleonly_n200 전체·겹침·비겹침·공통미관측</summary>


|월|부분집합|모델|N범위|support있는클래스범위|F1평균±SD(%)|정확도평균±SD(%)|
|---|---|---|---|---|---|---|
|202504|all|M0|237389–237389|20–20|17.746 ± 0.148|24.855 ± 0.570|
|202504|all|M1|237389–237389|20–20|32.216 ± 2.591|46.664 ± 3.700|
|202504|all|M2|237389–237389|20–20|36.625 ± 2.087|52.385 ± 2.570|
|202504|all|M3|237389–237389|20–20|16.116 ± 1.532|22.666 ± 3.062|
|202504|all|M4|237389–237389|20–20|16.077 ± 1.824|22.001 ± 3.367|
|202504|all|M5|237389–237389|20–20|16.643 ± 1.512|23.486 ± 3.021|
|202504|train_overlap|M0|1–6|1–5|0.000 ± 0.000|0.000 ± 0.000|
|202504|train_overlap|M1|1–6|1–5|0.000 ± 0.000|0.000 ± 0.000|
|202504|train_overlap|M2|1–6|1–5|0.000 ± 0.000|0.000 ± 0.000|
|202504|train_overlap|M3|1–6|1–5|0.000 ± 0.000|0.000 ± 0.000|
|202504|train_overlap|M4|1–6|1–5|0.000 ± 0.000|0.000 ± 0.000|
|202504|train_overlap|M5|1–6|1–5|1.000 ± 2.236|20.000 ± 44.721|
|202504|train_nonoverlap|M0|237383–237388|20–20|17.746 ± 0.148|24.856 ± 0.570|
|202504|train_nonoverlap|M1|237383–237388|20–20|32.216 ± 2.591|46.665 ± 3.700|
|202504|train_nonoverlap|M2|237383–237388|20–20|36.625 ± 2.087|52.386 ± 2.570|
|202504|train_nonoverlap|M3|237383–237388|20–20|16.116 ± 1.532|22.666 ± 3.062|
|202504|train_nonoverlap|M4|237383–237388|20–20|16.077 ± 1.824|22.002 ± 3.367|
|202504|train_nonoverlap|M5|237383–237388|20–20|16.643 ± 1.512|23.486 ± 3.020|
|202504|common_unseen|M0|235128–235128|20–20|17.772 ± 0.194|24.870 ± 0.498|
|202504|common_unseen|M1|235128–235128|20–20|32.435 ± 2.692|46.937 ± 3.681|
|202504|common_unseen|M2|235128–235128|20–20|36.810 ± 2.107|52.826 ± 2.610|
|202504|common_unseen|M3|235128–235128|20–20|16.253 ± 1.562|22.882 ± 3.091|
|202504|common_unseen|M4|235128–235128|20–20|16.202 ± 1.837|22.202 ± 3.392|
|202504|common_unseen|M5|235128–235128|20–20|16.772 ± 1.523|23.698 ± 3.036|
|202505|all|M0|233986–233986|20–20|17.205 ± 0.207|24.322 ± 0.598|
|202505|all|M1|233986–233986|20–20|31.563 ± 2.477|46.293 ± 3.559|
|202505|all|M2|233986–233986|20–20|36.265 ± 1.651|52.406 ± 2.433|
|202505|all|M3|233986–233986|20–20|15.848 ± 1.567|22.344 ± 3.244|
|202505|all|M4|233986–233986|20–20|15.827 ± 1.885|21.673 ± 3.565|
|202505|all|M5|233986–233986|20–20|16.346 ± 1.556|23.090 ± 3.174|
|202505|train_overlap|M0|1–5|1–3|0.800 ± 1.789|8.000 ± 17.889|
|202505|train_overlap|M1|1–5|1–3|0.800 ± 1.789|8.000 ± 17.889|
|202505|train_overlap|M2|1–5|1–3|0.800 ± 1.789|8.000 ± 17.889|
|202505|train_overlap|M3|1–5|1–3|0.000 ± 0.000|0.000 ± 0.000|
|202505|train_overlap|M4|1–5|1–3|0.000 ± 0.000|0.000 ± 0.000|
|202505|train_overlap|M5|1–5|1–3|0.000 ± 0.000|0.000 ± 0.000|
|202505|train_nonoverlap|M0|233981–233985|20–20|17.205 ± 0.207|24.322 ± 0.598|
|202505|train_nonoverlap|M1|233981–233985|20–20|31.563 ± 2.477|46.293 ± 3.559|
|202505|train_nonoverlap|M2|233981–233985|20–20|36.265 ± 1.651|52.407 ± 2.433|
|202505|train_nonoverlap|M3|233981–233985|20–20|15.848 ± 1.567|22.345 ± 3.244|
|202505|train_nonoverlap|M4|233981–233985|20–20|15.827 ± 1.885|21.673 ± 3.565|
|202505|train_nonoverlap|M5|233981–233985|20–20|16.346 ± 1.556|23.090 ± 3.174|
|202505|common_unseen|M0|232107–232107|20–20|17.221 ± 0.239|24.320 ± 0.561|
|202505|common_unseen|M1|232107–232107|20–20|31.740 ± 2.551|46.514 ± 3.532|
|202505|common_unseen|M2|232107–232107|20–20|36.416 ± 1.671|52.778 ± 2.463|
|202505|common_unseen|M3|232107–232107|20–20|15.953 ± 1.580|22.521 ± 3.269|
|202505|common_unseen|M4|232107–232107|20–20|15.930 ± 1.892|21.838 ± 3.587|
|202505|common_unseen|M5|232107–232107|20–20|16.452 ± 1.564|23.266 ± 3.190|

빈부분집합은N/A. 고정클래스수에서support없는클래스처리규칙을유지한다. 희소겹침집단은전체서비스성능추정이아니다.

</details>
<details><summary>googleonly_n200 서비스별F1과교사·학생의주요혼동</summary>


|월|서비스|support|M0|M1|M2|M3|M4|M5|
|---|---|---|---|---|---|---|---|---|
|202504|google-www|22292|20.930|38.373|43.847|5.806|5.540|5.156|
|202504|google-play|12556|26.983|46.104|56.793|33.330|33.662|33.999|
|202504|google-services|16790|36.939|45.239|55.390|25.053|24.240|24.883|
|202504|google-gstatic|16310|42.342|54.423|59.410|36.416|38.401|38.118|
|202504|google-usercontent|19125|23.779|63.292|54.297|40.233|41.436|41.624|
|202504|google-authentication|7616|16.173|46.762|47.838|24.859|24.464|24.903|
|202504|google-fonts|7884|24.773|29.633|32.123|16.486|17.717|18.191|
|202504|google-drive|511|3.868|5.185|9.010|5.671|5.758|5.525|
|202504|google-docs|973|8.660|16.433|23.234|8.532|8.439|8.138|
|202504|google-photos|331|1.640|7.306|11.630|0.880|0.867|0.937|
|202504|google-translate|518|2.214|5.521|6.224|4.408|4.646|4.857|
|202504|youtube|60171|27.019|64.976|68.426|33.685|32.076|33.701|
|202504|google-hangouts|62|1.301|3.524|5.935|0.292|0.322|0.308|
|202504|google-ads|41712|36.002|33.784|45.653|14.268|11.242|14.498|
|202504|google-safebrowsing|1657|17.953|44.004|46.677|9.552|11.406|11.099|
|202504|google-recaptcha|1016|15.100|10.197|13.496|11.153|10.887|10.898|
|202504|google-imasdk|551|2.643|3.992|5.025|2.255|2.109|2.173|
|202504|google-calendar|24584|29.843|69.056|68.717|32.512|30.720|34.223|
|202504|google-autofill|532|11.427|31.265|49.566|6.464|6.978|7.239|
|202504|firebase-crashlytics|2198|5.339|25.249|29.206|10.456|10.626|12.385|
|202505|google-www|22661|20.978|38.850|44.432|5.792|5.610|5.310|
|202505|google-play|12307|25.240|43.867|53.893|32.201|32.301|32.694|
|202505|google-services|16838|37.246|44.095|56.080|26.169|25.341|26.161|
|202505|google-gstatic|15724|41.096|52.940|59.175|34.068|36.104|35.920|
|202505|google-usercontent|18222|23.378|62.945|53.237|39.348|40.599|40.646|
|202505|google-authentication|6976|14.528|46.135|46.376|24.544|24.288|24.348|
|202505|google-fonts|7762|24.785|29.434|31.944|17.011|18.233|18.772|
|202505|google-drive|504|3.610|4.679|8.420|5.029|5.190|4.615|
|202505|google-docs|879|8.006|15.464|21.938|7.641|7.718|7.273|
|202505|google-photos|361|1.482|8.046|11.301|1.008|1.043|1.066|
|202505|google-translate|466|2.063|4.985|5.542|5.268|5.195|5.479|
|202505|youtube|61631|26.465|65.002|68.670|33.144|31.640|33.053|
|202505|google-hangouts|61|0.784|2.737|4.826|0.172|0.174|0.164|
|202505|google-ads|39760|35.597|32.955|44.411|14.159|11.072|14.151|
|202505|google-safebrowsing|1587|16.834|42.367|45.568|9.735|11.644|11.411|
|202505|google-recaptcha|992|13.627|9.753|12.155|10.439|10.396|10.178|
|202505|google-imasdk|640|3.061|4.372|5.113|2.505|2.375|2.371|
|202505|google-calendar|24153|29.729|68.631|68.963|32.844|30.996|34.711|
|202505|google-autofill|543|10.634|30.774|47.114|6.702|7.344|7.678|
|202505|firebase-crashlytics|1919|4.966|23.222|36.141|9.179|9.280|10.918|

같은평가플로우에대한5개모델혼동행렬합계이며서로다른플로우5배가아니다. 행=정답,열=예측.

|월|모델|정답→예측|5반복오분류합|
|---|---|---|---|
|202504|M2|google-ads→google-www|30243|
|202504|M2|youtube→google-ads|22646|
|202504|M2|google-ads→youtube|20053|
|202504|M2|google-usercontent→google-calendar|18575|
|202504|M2|google-ads→google-fonts|16818|
|202504|M5|youtube→firebase-crashlytics|40923|
|202504|M5|google-ads→firebase-crashlytics|38935|
|202504|M5|google-usercontent→google-calendar|30841|
|202504|M5|youtube→google-usercontent|28415|
|202504|M5|google-calendar→firebase-crashlytics|27093|
|202505|M2|google-ads→google-www|29976|
|202505|M2|youtube→google-ads|23336|
|202505|M2|google-ads→youtube|19287|
|202505|M2|google-usercontent→google-calendar|18200|
|202505|M2|google-ads→google-fonts|16560|
|202505|M5|youtube→firebase-crashlytics|44302|
|202505|M5|google-ads→firebase-crashlytics|37973|
|202505|M5|google-usercontent→google-calendar|29722|
|202505|M5|youtube→google-usercontent|29234|
|202505|M5|google-calendar→firebase-crashlytics|27089|


</details>

## 후속 실험 해석 — 무엇을 확인했고, 다음에 무엇을 바꿔야 하는가

**검토 기준: 2026-10-31, 회수·검증한 본실험 180회.** 여기에는 대표 30회와 이번 후속 150회가 포함된다. 개발 후보 60회는 설정 선택 자료로 따로 센다. 아래의 %는 Macro-F1을 100배 표시한 값이고, 차이는 %p다. ±는 seed 201~205의 표본 표준편차(SD)다. 신뢰구간이나 통계적 유의성 표시가 아니다. 동일 평가 플로우에 다섯 모델을 적용했으므로 평가 표본도 다섯 배로 세지 않는다.

### 1. 발표에서 먼저 전달할 결론

**통제한 비교 실험은 끝났지만, ‘교사 성능을 거의 유지하는 경량화’ 목표는 달성하지 못했다.** 대표 혼합20·200개/클래스의 4월 Macro-F1은 교사 M2 53.771%, 직접학습 학생 M3 32.493%, 증류 학생 M5 32.743%다. M5는 M3보다 평균 0.250%p 높지만, M2보다 21.028%p 낮다. 계획한 교사 대비 손실 2%p 이내와는 차이가 크다. 파라미터 34.47배 축소와 지정 CPU의 batch1 지연 약 8.86배 감소는 확인했다. 성능 보존과 경량성은 별개로 판정해야 한다.

후속 조건에서도 비슷한 구조가 나타났다. 라벨 수를 늘리면 학생 자체의 성능은 크게 좋아졌지만, 현재 방식의 KD가 직접학습에 더하는 평균 이득은 작았다. Google 내부 구분은 교사에게도 어렵고, Google을 제외한 구성에서도 교사와 학생의 큰 차이가 남았다. 따라서 ‘Google 때문에만 실패했다’거나 ‘좋은 교사를 만들기만 하면 학생도 좋아진다’는 설명은 결과를 충분히 설명하지 못한다.

현재 결과를 활용하는 방향은 **사전학습 활용의 이점과 학생의 성능 손실을 함께 제시하고, 작은 학생의 표현·용량·학습 방식을 다음 연구 질문으로 좁히는 것**이다. 이 문서의 후속 제안은 아직 실행하지 않았다.

### 2. 질문을 어떻게 실험으로 바꿨는가

이 실험은 CESNET-QUICEXT-25-XS의 서비스 라벨을 예측하는 폐쇄형 분류다. 첫 최대 30패킷의 간격(IPT), 방향(DIR), 크기(SIZE)를 관측한다. 도메인 문자열·SNI·IP·payload·플로우 전체 통계는 이번 모델 입력에 없다. 정답은 학습 손실과 평가에 사용하고 추론 입력에는 넣지 않는다.

|모델|만든 이유|실제로 학습한 것|비교에서 답하는 질문|
|---|---|---|---|
|M0|작은 신경망을 쓰기 전에 확인할 전통적 기준선|같은 30-PPI에서 구한 16통계로 LightGBM 학습|복잡한 신경망 없이도 어느 정도 가능한가?|
|M1|공개 사전학습 활용의 비교 기준|교사와 같은 본체 구조를 공개 학습 가중치 없이 목표 정답으로 학습|현재 데이터만으로 큰 모델이 배우는 수준은?|
|M2|적은 목표 라벨로 좋은 교사를 만들기|30pktTCNET 계열 공개 backbone을 목표 서비스에 전체 미세조정|명시한 사전학습 활용 절차가 도움이 되는가?|
|M3|KD 없는 학생의 기준 성능|작은 CNN을 실제 정답 CE로 학습|작은 모델을 직접 학습하면 어느 정도인가?|
|M4|무작위 초기화에서 학습한 교사의 KD 효과 확인|M1의 확률 + 실제 정답으로 M3와 같은 학생 학습|목표 데이터로 만든 교사의 지식은 도움이 되는가?|
|M5|사전학습 교사를 학생으로 옮기는 핵심 방법|M2의 확률 + 실제 정답으로 동일 학생 학습|좋은 교사의 이점이 작은 학생에게 전달되는가?|

20클래스 교사는 695,593개, 학생은 20,180개 파라미터다. 학생은 Conv1d 3층(3→32→64→64, 커널 3), 각 층 ReLU·유효 위치 마스크, masked mean pooling, 분류 head다. 교사의 공개 256차원 wrapper를 그대로 분류기에 붙인 것이 아니라 refinement와 neck을 제외한 pooled 448차원에 새 분류 head를 붙였다. 자세한 모듈·shape·초기값은 구조 snapshot과 설계 절에 보존했다. M1의 데이터 비의존 PLE 초기화는 유지하므로 ‘모든 숫자가 무작위’라고 설명하지 않는다.

1월 학습 후보를 canonical 30-PPI로 정제했다. 같은 입력·같은 라벨은 대표 하나를 남기고, 같은 입력·다른 라벨은 그룹 전체를 학습 후보에서 제외했다. 그 뒤 서비스당 균등 추출했다. 같은 seed에서 50 ⊂ 100 ⊂ 200 ⊂ 1000으로 중첩하며 모델끼리 동일 입력을 쓴다. **4·5월 평가 기록은 자연 빈도를 유지하고 자연 반복·충돌을 지우지 않는다.** 실제 학습 입력과 겹치는 부분만 별도 표로 분해했다.

2월 균형 검증셋으로 개발 seed 101/102에서 학습률과 공통 KD를 골랐다. 본실험은 seed 201~205에서 고정 설정으로 진행했다. M1 LR=0.001, M2 LR=0.0001, 학생 LR=0.003, M0 leaves=31, 공통 KD α=0.5·T=1이다. KD는 0.5×정답 CE + 0.5×교사 확률 KL이며 일반 구현에는 T² 보정이 있다. M3/M4/M5의 초기값·표본·shuffle을 맞추고, 교사는 같은 구성·라벨 예산·seed의 checkpoint를 사용했다. **추가 무라벨 입력 풀은 사용하지 않았다.** 따라서 ‘같은 정답 입력에서 KD를 더한 효과’의 실험이다.

4월이 사전 지정 주평가이고 5월은 시간차 재평가다. 두 달 모두 과거에 살펴본 자료이므로 프로젝트 전체에서 완전히 미사용한 외부 검증은 아니다. 50개 조건도 개발 과정 전체에 서비스당 50개 라벨만 접근했다는 뜻은 아니다. 정제에 후보 라벨을 사용했고, 설정은 대표 200개 개발 조건과 2월 검증으로 선택했다.

### 3. 질문 1 — 정답 학습 입력을 늘리면 무엇이 달라지는가?

**방법.** Google 포함 혼합20 목록과 2월 검증·4월 평가를 유지하고 클래스당 학습 입력을 50/100/200/1000개로 바꿨다. 아래는 4월 전체 유효 평가 기록 379,194개에 대한 5회 평균 ± SD다.

|클래스당 입력|M0|M1|M2|M3|M4|M5|
|---|---|---|---|---|---|---|
|50|29.233 ± 0.982|40.651 ± 1.032|42.319 ± 1.691|19.088 ± 0.886|18.909 ± 0.866|19.475 ± 0.902|
|100|31.830 ± 0.691|46.675 ± 0.322|49.310 ± 1.721|26.140 ± 0.819|26.310 ± 0.837|26.463 ± 0.921|
|200|34.075 ± 0.379|50.332 ± 1.617|53.771 ± 1.743|32.493 ± 0.982|32.451 ± 0.736|32.743 ± 0.815|
|1000|38.623 ± 0.334|58.396 ± 1.181|62.475 ± 0.820|46.098 ± 0.243|46.423 ± 0.489|46.342 ± 0.599|

**관찰과 해석.** M5는 50개에서 19.475%, 1000개에서 46.342%로 26.867%p 높아졌다. M2도 42.319%에서 62.475%로 20.156%p 높아졌다. 이번 범위에서는 더 많은 정답 입력을 주는 변화가, 같은 예산에서 KD 유무를 바꾸는 변화보다 훨씬 컸다. 다만 두 조작의 비용도 다르므로 ‘라벨 확보가 항상 더 경제적’이라는 결론까지 내리지는 않는다.

50/100/200개에서는 M0가 세 학생보다 높았고, 1000개에서는 학생이 M0보다 높았다. 예를 들어 200개에서 M0 34.075% 대 M5 32.743%, 1000개에서는 M0 38.623% 대 M5 46.342%다. 적은 데이터에서 통계 기반 트리가 경쟁력 있는 기준선이며, 학생 신경망의 이점은 데이터 규모에 따라 달라질 수 있다.

**한계.** 신경망은 모두 50epoch지만 20클래스의 업데이트 수는 400/800/1600/7850회다. 표본 수가 늘면 계산량도 늘었다. 따라서 이는 고정 학습 일정에서의 라벨 예산 비교이며 라벨의 순수 효과만 분리한 고정 업데이트 실험은 아니다. 같은 설정을 다른 예산에 적용했으므로 예산마다 최적 설정을 다시 찾은 결과도 아니다.

**이 결과에서 이어지는 질문.** 추가 라벨 확보와 학생 구조 개선 중 어디에 자원을 쓸지 비교할 근거가 생겼다. 계산량을 고정한 비교가 필요하다면 다음 실험에서 별도로 설계해야 한다. 현재 표의 결과를 바꾸기 위해 업데이트 수를 소급해서 바꾸지 않는다.

### 4. 질문 2 — 사전학습으로 좋아진 교사가 더 좋은 학생을 만드는가?

M2−M1은 사전학습 활용 절차의 차이, M5−M3은 학생에 KD를 추가한 차이, M5−M4는 교사를 M1에서 M2로 바꾼 차이다. 모두 같은 seed끼리 먼저 뺀 뒤 다섯 차이를 요약했다. 아래 괄호는 차이가 양수인 반복 수다.

|4월 조건|M2−M1 평균±SD (%p)|M5−M3 평균±SD (%p)|M5−M4 평균±SD (%p)|M2−M5 평균±SD (%p)|
|---|---|---|---|---|
|혼합20 · 50개|+1.667 ± 2.370 (4/5)|+0.387 ± 0.400 (4/5)|+0.566 ± 0.528 (4/5)|+22.844 ± 2.334 (5/5)|
|혼합20 · 100개|+2.636 ± 2.011 (4/5)|+0.323 ± 0.773 (4/5)|+0.153 ± 0.636 (3/5)|+22.847 ± 2.564 (5/5)|
|혼합20 · 200개|+3.439 ± 2.754 (4/5)|+0.250 ± 0.499 (4/5)|+0.292 ± 0.463 (3/5)|+21.028 ± 2.276 (5/5)|
|혼합20 · 1000개|+4.079 ± 1.178 (5/5)|+0.244 ± 0.570 (4/5)|-0.080 ± 0.291 (2/5)|+16.133 ± 1.212 (5/5)|
|비Google13 · 200개|+1.963 ± 1.898 (5/5)|+0.339 ± 1.078 (3/5)|+0.295 ± 0.946 (2/5)|+31.977 ± 2.816 (5/5)|
|Google계열20 · 200개|+4.409 ± 4.303 (4/5)|+0.527 ± 0.435 (5/5)|+0.566 ± 0.533 (4/5)|+19.982 ± 2.669 (5/5)|

**첫째, 교사 수준에서 사전학습 활용의 평균 이점은 모든 구성에서 관찰됐다.** 다만 M1과 M2는 초기 가중치 외에 선택 학습률과 BatchNorm 처리도 다르다. M2는 공개 running 통계를 유지하며 학습 가능한 가중치를 미세조정한다. 따라서 표의 차이는 현재의 적응 정책을 포함한 비교이고, ‘가중치만 바꾼 인과효과’는 아니다. Google계열20에서 평균 +4.409%p라도 한 seed는 −2.081%p였다는 점도 남긴다.

**둘째, KD가 직접학습 학생에 추가한 이득은 작았다.** 4월 M5−M3 평균은 여섯 조건에서 +0.244~+0.527%p다. 대표 200개는 −0.593 / +0.378 / +0.333 / +0.739 / +0.394%p이며, 비Google13은 −1.060%p인 반복도 있다. Google계열20의 4월은 다섯 번 모두 양수지만 5월에는 네 번만 양수다. 이것은 관찰된 방향과 변동이며, 유의성 검정이나 새로운 독립 데이터에서 재현된 보편적 효과라고 주장하지 않는다.

**셋째, 더 좋은 교사의 이점이 학생에 그대로 옮겨지지 않았다.** 혼합20·1000개에서 M2는 M1보다 평균 +4.079%p 높지만, M5는 M4보다 −0.080%p 낮았다. 차이가 작아 M4의 확정적 우위라고 해석할 수는 없지만, 강한 교사를 쓰면 반드시 학생도 좋아진다는 가정은 지지하지 않는다. 학생의 표현·최적화, 동일 라벨 입력만 사용한 KD 방식, 교사 오류와 확률의 성질 등이 후보 설명이다. 어느 것이 주원인인지는 현재 결과만으로 분리되지 않는다.

**넷째, 학생과 교사의 큰 격차는 모든 구성에서 남았다.** 4월 평균 격차는 혼합20·1000개에서 16.133%p로 줄었지만, 비Google13·200개에서는 31.977%p다. 비Google 조건에서 교사는 80.171%까지 올라가도 학생은 48.194%에 머물렀다. 학생 문제를 Google 구분의 어려움 하나로 돌릴 수 없다.

**다음 질문.** 교사만 더 키우기보다 학생의 용량·정보 표현·풀링·학습 시간 중 어떤 요인이 격차를 만드는지 우선 분리할 필요가 있다. 실제 실행 전에는 비교 한 가지와 판단 기준을 정해야 한다. 본 실험의 선택값을 4·5월 결과를 보고 다시 탐색하지 않았다.

### 5. 질문 3 — Google 서비스를 왜 어렵게 구분하는가?

**방법.** 라벨 예산을 서비스당 200개로 맞추고 혼합20, 비Google13, Google계열20을 따로 학습했다. 이는 서로 다른 분류 문제다. 클래스 수뿐 아니라 경쟁 클래스와 표본 분포도 달라 ‘Google 추가의 순수 효과’로 해석할 수 없다.

|4월 구성|평가 플로우|M0|M1|M2|M3|M4|M5|
|---|---|---|---|---|---|---|---|
|혼합20 · 200개|379,194|34.075 ± 0.379|50.332 ± 1.617|53.771 ± 1.743|32.493 ± 0.982|32.451 ± 0.736|32.743 ± 0.815|
|비Google13 · 200개|252,471|62.369 ± 0.503|78.208 ± 1.273|80.171 ± 1.549|47.855 ± 2.517|47.899 ± 2.399|48.194 ± 1.684|
|Google계열20 · 200개|237,389|17.746 ± 0.148|32.216 ± 2.591|36.625 ± 2.087|16.116 ± 1.532|16.077 ± 1.824|16.643 ± 1.512|

평균 점수만 보면 원인이 드러나지 않는다. 아래는 대표 혼합20의 4월에서 해석에 도움이 되는 서비스다. support는 실제 평가 플로우 수이며 다섯 seed의 합이 아니다.

|서비스|support|M2 F1(%)|M5 F1(%)|M2 정밀도(%)|M2 재현율(%)|
|---|---|---|---|---|---|
|instagram|53247|99.718|93.198|99.885|99.552|
|snapchat|57813|93.154|66.261|95.829|90.637|
|youtube|60171|68.214|36.554|79.540|59.793|
|google-www|22292|47.688|6.568|46.538|49.210|
|google-drive|511|8.089|4.620|4.524|39.256|
|google-translate|518|5.232|3.844|2.828|36.641|
|google-imasdk|551|5.988|1.524|3.356|28.276|

Drive는 M2가 실제 Drive의 약 39.256%를 찾지만, Drive라고 예측한 것 중 실제 Drive인 비율은 4.524%에 불과하다. 따라서 F1은 8.089%다. ‘전혀 못 찾는다’보다는 다른 서비스를 Drive로 잘못 예측하는 문제가 크다. 반대로 M5의 Google WWW는 재현율 4.572%라서 실제 WWW를 놓치는 문제가 크다. 낮은 F1도 원인이 같지 않다.

Google계열20의 M5는 Firebase Crashlytics 재현율이 82.684%지만 정밀도는 6.810%, F1은 12.385%다. 다섯 혼동행렬을 합치면 YouTube→Crashlytics 40,923건, Ads→Crashlytics 38,935건이 보인다. 이는 같은 평가 플로우를 다섯 모델로 예측한 합계이지 서로 다른 플로우 79,858개가 아니다. 특정 희소 클래스로 과하게 예측하는 현상과 함께 읽어야 한다. 교사 M2도 Google계열20에서 Ads→WWW가 30,243건으로 주요 혼동이었다.

비Google13에서도 M5의 Facebook Graph→WhatsApp 63,275건, Graph→Instagram 54,354건의 합산 혼동이 남았다. 즉 Google 외의 가까운 서비스들 사이에서도 학생이 구분을 놓친다. 혼합20에서 Instagram M2 F1은 99.718%지만 비Google13에서는 90.582%였다. 평가의 Instagram 기록이 같더라도 경쟁 클래스와 학습 문제가 바뀌면 정밀도와 F1이 바뀔 수 있다는 사례다.

**표본 수의 한계도 중요하다.** 서비스 자격 ≥1000은 1월 정제 학습 후보의 기준이다. 모든 평가 월에 1000개가 있다는 뜻은 아니다. Google계열20의 4월 Hangouts는 62개, Photos는 331개다. Hangouts의 M5 F1 0.308%를 기록하되, 이런 희소 서비스의 점수를 매우 정밀한 일반화 추정이라고 해석하지 않는다. Macro-F1은 각 서비스를 같은 비중으로 평균하므로 희소 클래스도 전체 점수에 영향을 준다. 이를 보고 뒤늦게 희소 클래스를 제외하면 평가 과제가 달라진다.

**알 수 있는 것과 없는 것.** 제한된 PPI 표현에서 특정 서비스의 오탐·누락이 많다는 것은 확인했다. 공통 인프라, 트래픽 형태의 유사성, 짧은 플로우, 모델 표현과 시간 변화가 각각 얼마나 기여했는지는 아직 분리하지 않았다. 모델 입력에 도메인이 없다고 라벨 정의와 네트워크 환경의 영향을 없앤 것도 아니다. 발표에서는 관찰된 혼동을 먼저 보이고, 원인 설명은 검증할 가설로 구분한다.

### 6. 질문 4 — 학습 입력과 겹친 평가 데이터 때문에 높게 나온 것인가?

주 결과 All은 자연 평가 기록 전체다. Train-overlap은 해당 seed·예산의 실제 학습 PPI와 정확히 같은 평가 입력, Train-nonoverlap은 이를 뺀 집합이다. Common-unseen은 미리 지정한 본실험 5seed 최대1000·개발 2seed200·고정 검증의 PPI 합집합과 모두 다른 평가 입력이다. 원본 source ID가 같다는 뜻과 PPI가 같다는 뜻도 구분했다.

아래는 seed에 따라 달라지는 overlap 수와 support가 있는 클래스 수 범위다. 0인 경우 성능은 N/A다.

|조건|4월 All|4월 겹침 N / 클래스|5월 All|5월 겹침 N / 클래스|
|---|---|---|---|---|
|혼합20 · 50개|379,194|0~2 / 0~1|365,258|0~6 / 0~2|
|혼합20 · 100개|379,194|0~5 / 0~2|365,258|0~6 / 0~2|
|혼합20 · 200개|379,194|0~7 / 0~4|365,258|2~6 / 1~4|
|혼합20 · 1000개|379,194|16~56 / 6~9|365,258|19~160 / 7~9|
|비Google13 · 200개|252,471|6~28 / 3~4|225,067|5~31 / 3~3|
|Google계열20 · 200개|237,389|1~6 / 1~5|233,986|1~5 / 1~3|

전체 6조건×6모델×2개월에서 All과 Train-nonoverlap의 5seed 평균 Macro-F1 차이는 절댓값 최대 약 0.00692%p였다. 따라서 **이번 정의의 실제 fitting PPI 중복이 전체 점수를 크게 끌어올렸다는 증거는 없다.** 겹침 집단 자체가 매우 작고, 대부분의 클래스에 support가 없기 때문에 그 집단의 점수로 전체 서비스 암기 성능을 설명하면 안 된다. 부분집합에서도 고정 클래스 목록의 Macro-F1 계산 규칙을 유지했다.

4월 Common-unseen은 혼합20 376,465개, 비Google13 251,691개, Google계열20 235,128개다. 혼합20의 M5는 All에서 19.475→26.463→32.743→46.342%, 공통 미관측에서는 19.578→26.605→32.955→46.472%로 라벨 증가에 따른 방향이 유지됐다. 전체 조건·모델·월에서 Common-unseen 평균과 All 평균의 최대 차이는 약 0.344%p였다. 이는 정의한 미관측 집합에서의 보조 결과이며, 새로운 환경·기기·세션이나 사전학습 원천까지 모두 독립임을 증명하지 않는다.

평가의 중복을 전부 삭제해 더 좋은 점수만 발표하는 대신, 자연 분포 결과와 겹침 분해를 함께 보존한 이유가 여기에 있다. 유효 패킷 길이별 표본 수는 데이터 원장에 있지만, short/long별 성능은 이 네 부분집합의 통합 성능표에 별도로 집계하지 않았다. 그 분석까지 완료했다고 말하지 않는다.

### 7. 질문 5 — 50epoch 동안 제대로 학습했는가, 월이 바뀌면 유지되는가?

50epoch는 본실험 전에 동결한 공통 신경망 학습 상한이다. 매 epoch 검증 지표·학습 손실·업데이트 수·best/last를 저장했다. 아래는 교사 M2와 학생 M5의 2월 검증 곡선을 다섯 seed에서 평균한 값이다. ‘best 평균’은 각 seed의 검증 최고 checkpoint 값의 평균이며, 한 공통 epoch를 사후 선택한 값이 아니다.

|조건|모델|선택 epoch (seed201~205)|epoch10 F1|epoch30 F1|epoch50 F1|best 평균 F1|
|---|---|---|---|---|---|---|
|혼합20 · 50개|M2|50, 50, 47, 45, 48|28.742|53.105|55.191|55.202|
|혼합20 · 50개|M5|47, 43, 37, 44, 43|14.520|25.185|26.623|26.810|
|혼합20 · 100개|M2|46, 44, 45, 50, 34|45.823|63.749|64.741|64.796|
|혼합20 · 100개|M5|38, 42, 42, 40, 34|20.064|34.817|36.488|36.769|
|혼합20 · 200개|M2|43, 37, 40, 35, 46|59.650|70.007|70.310|70.465|
|혼합20 · 200개|M5|44, 46, 45, 39, 45|28.925|42.881|44.761|44.984|
|혼합20 · 1000개|M2|41, 34, 36, 34, 33|75.139|78.042|78.240|78.549|
|혼합20 · 1000개|M5|45, 49, 50, 44, 43|46.477|58.778|60.347|60.425|
|비Google13 · 200개|M2|36, 31, 41, 29, 43|86.935|92.676|92.798|92.973|
|비Google13 · 200개|M5|39, 42, 48, 49, 47|42.187|62.388|64.857|65.003|
|Google계열20 · 200개|M2|41, 37, 44, 35, 37|51.407|62.979|63.324|63.528|
|Google계열20 · 200개|M5|40, 33, 44, 48, 47|23.359|32.046|34.560|34.772|

대표 200개에서는 마지막 epoch 전에 best가 선택됐고, 후반 검증 곡선은 비교적 평탄했다. 하지만 혼합20·50개의 M2는 두 seed에서 50epoch가 best였으며, 100개 M2와 1000개 M5에도 마지막 epoch 선택이 있었다. 따라서 ‘모든 조건이 충분히 수렴했다’는 결론은 내리지 않는다. Cosine 일정이 끝나면서 학습률이 작아져 평탄해질 수도 있다. 교사·학생 격차를 모델 용량만의 한계로 단정할 근거도 부족하다.

대표 M2의 검증 최고 평균은 70.465%인데 4월은 53.771%, M5는 44.984%에서 32.743%로 달라졌다. 이 차이를 전부 시간 변화 탓으로 돌리면 안 된다. 2월은 클래스당 최대200의 균형 검증이고 4월은 자연 분포이며, checkpoint 선택에 쓴 자료와 평가 자료의 역할도 다르다. Macro-F1 역시 각 클래스 정밀도를 통해 예측 오탐과 클래스 빈도의 영향을 받는다.

|조건|M2 4월|M2 5월|M5 4월|M5 5월|M5−M3 5월 (%p)|
|---|---|---|---|---|---|
|혼합20 · 50개|42.319 ± 1.691|42.151 ± 1.540|19.475 ± 0.902|19.689 ± 0.914|+0.390 ± 0.369 (4/5)|
|혼합20 · 100개|49.310 ± 1.721|49.379 ± 1.473|26.463 ± 0.921|26.697 ± 0.895|+0.311 ± 0.728 (4/5)|
|혼합20 · 200개|53.771 ± 1.743|53.680 ± 1.456|32.743 ± 0.815|32.990 ± 0.805|+0.213 ± 0.518 (4/5)|
|혼합20 · 1000개|62.475 ± 0.820|62.159 ± 0.693|46.342 ± 0.599|46.176 ± 0.645|+0.284 ± 0.551 (4/5)|
|비Google13 · 200개|80.171 ± 1.549|79.062 ± 1.756|48.194 ± 1.684|48.453 ± 1.634|+0.316 ± 0.981 (3/5)|
|Google계열20 · 200개|36.625 ± 2.087|36.265 ± 1.651|16.643 ± 1.512|16.346 ± 1.556|+0.498 ± 0.464 (4/5)|

4월과 5월에서 주요 순위와 작은 KD 이득의 양상은 비슷했다. 이는 두 월에서의 관찰이다. 같은 seed 모델과 관련된 서비스 분포를 반복 평가한 것이므로 독립 반복이 두 배로 늘었다고 세지 않으며, 두 달만으로 장기 안정성이나 다른 망에서의 성능을 보장하지 않는다.

### 8. 질문 6 — CPU에서 쓸 수 있을 만큼 작고 빠른가?

**방법.** 모든 본실험 모델 180개를 Apple M5 CPU 1스레드·FP32에서 각각 새 프로세스로 측정했다. 같은 구성의 고정 128개 검증 입력을 사용했다. batch1은 warm-up100회 뒤 1000회, batch128은 warm-up10회 뒤 100회다. M0에는 16통계 추출을 포함하고 신경망에는 내부 고정 변환·embedding을 포함했다. 입력은 이미 메모리에 있으며 패킷 도착 대기·캡처·디스크 읽기·array→tensor 준비는 제외했다. OS와 라이브러리 버전, 원시 측정값, checkpoint 해시는 각 benchmark.json에 있다.

아래는 대표 혼합20·200개의 결과다. 중앙값·p95는 각 모델 반복에서 구한 후 다섯 seed를 평균한 값이며, 원시 지연을 전부 합친 단일 p95가 아니다.

|모델|4월 F1(%)|파라미터|batch1 중앙값(ms)|batch1 p95(ms)|batch128 flows/s|추론 파일(MiB)|warm RSS(MiB)|
|---|---|---|---|---|---|---|---|
|M0|34.075|트리|0.309854|0.386140|7571|7.229|297.0|
|M1|50.332|695593|0.349533|0.416905|98|2.724|276.0|
|M2|53.771|695593|0.352775|0.571007|99|2.724|276.2|
|M3|32.493|20180|0.039771|0.058091|6986|0.080|263.4|
|M4|32.451|20180|0.040179|0.048969|7101|0.080|263.3|
|M5|32.743|20180|0.039833|0.064596|7036|0.080|263.6|

M5는 M2보다 약 34.47배 적은 파라미터를 쓰고 batch1 중앙값 평균은 약 8.86배 짧았다. 따라서 크기·지연 감소 목표는 이 지정 환경에서 확인했다. 그러나 M2와 M5의 warm RSS는 약 276.2MiB와 263.6MiB여서 프로세스 메모리가 같은 비율로 줄지는 않았다. Python·Torch·할당자 등 공통 실행 환경이 포함되기 때문이다. 추론용 가중치 파일과 optimizer까지 들어 있는 학습 checkpoint의 크기도 구분했다.

교사의 batch128 처리량은 대표 조건 약 99flow/s, 후속 조건에서도 약 104~108flow/s였으며 batch1 시간만으로 예상한 값보다 낮았다. 원시 측정값과 계산은 검증했지만 원인은 분석하지 않았다. CPU backend·배치 크기의 영향을 받을 수 있으므로 ‘이 교사 구조는 어디서나 100flow/s만 처리한다’고 일반화하지 않는다. 학생은 후속 조건에서 약 7,117~7,422flow/s였고, 비Google13의 M0는 약 24,617flow/s로 해당 학생보다 높았다. 한 요청의 지연과 묶음 처리량은 별도 판단 지표다.

호스트의 다른 작업을 완전히 배제하지 않았고 모델 순서는 seed마다 M0→M5로 고정했다. 0.001ms 수준의 작은 차이를 학습 방식의 본질적 차이로 해석하지 않는다. M3/M4/M5의 추론 구조는 같으므로 증류 자체가 추론 연산을 추가하지 않으며, 학생 단독 시연에는 교사가 필요하지 않다.

**목표 판정.** 대표 조건의 파라미터 5배 이상 축소와 지정 CPU 지연 감소는 충족했다. 교사 대비 Macro-F1 손실 2%p 이내는 평균 21.028%p로 미달했고 다섯 seed 모두 미달했다. 다른 모든 구성에서도 격차가 남았다. 따라서 ‘성능을 보존하면서 압축했다’고 발표할 수 없고, ‘비용을 줄인 학생의 성능 손실을 정량화했고 현재 KD로는 충분히 회복하지 못했다’고 발표해야 한다.

### 9. 실행·회수·검증과 완료의 정확한 범위

이번 후속은 150fit, 신경망 월별 평가 250건, 로컬 M0 월별 평가 50건, CPU 모델 비용 측정 150건이다. 기존 대표 30fit·60평가·30CPU 측정과 합치면 본실험 180fit·360월별 평가·180CPU 측정이다. 개발 설정 탐색 60fit와 짧은 연결/속도 점검은 따로 기록한다. 소실되어 회수하지 못한 PID2161의 30fit는 유효 결과 수에 넣지 않았다.

후속 원본 11개 ZIP(단계별 학습5·평가5·운영기록1), 총 1,867,641,943바이트를 로컬에 보존했다. 전체 SHA256·ZIP CRC·안전 경로·내부 파일 해시·입력 ID·50epoch·교사 대응·초기값·예측 기반 지표를 검증했다. 환경과 로그도 남겼다. 후속 A100은 로컬 보존 확인 뒤 **2026-10-31 03:07:35 KST**에 해제했다. 원격 실행 약 76.21분은 결과 회수 대기까지 포함한 GPU 점유시간이나 실제 청구시간이 아니다. 일반 다운로드 실패와 조각 회수, 복구 중 도구 reset도 운영 기록에 남겼다.

로컬 후처리는 4시간 상한 안에서 약 152.5분에 완료됐다. 이미 학습된 M0의 평가와 CPU 비용 측정이며 새 CPU 본학습이 아니다. 결과가 마음에 들지 않는다고 범위를 늘리거나 A100에 재접속하지 않았다.

CPU 재생 시연은 대표 seed201을 미리 지정하고 고정 공개 PPI 표본을 사용한다. 6표본×6모델=36개 CPU 예측 라벨이 저장된 평가 예측과 일치하는지 점검했고, 학생만 로드한 브라우저 시연도 확인했다. 이것은 모든 입력의 bitwise 동일성을 증명하거나 실제 네트워크 패킷 수집을 구현한 것은 아니다. 잘못 맞힌 예시도 정답과 함께 그대로 표시한다.

완료한 것은 동결한 필수 실험, 결과 검증, 비용 측정, 해석과 발표 흐름·Q&A, 저장 PPI CPU 재생이다. 학교 양식의 실제 PPT 제작·제출·발표 시간 확인, 실시간 캡처, 새 환경·미등록 서비스·이상탐지, 선택 확장은 완료로 표시하지 않는다.

### 10. 팀 회의에서 결정할 다음 행동

**우선 제안은 주제를 즉시 버리기보다 목표를 더 정확하게 좁히는 것이다.** ‘사전학습과 KD로 높은 성능을 유지한 경량 모델 완성’은 현재 결과가 지지하지 않는다. 대신 ‘제한된 PPI와 라벨 예산에서 사전학습의 이점이 작은 학생으로 얼마나 전달되는지, 어느 지점에서 성능과 비용의 교환이 발생하는지’는 지금의 자료로 설명할 수 있다. 중간발표에서는 성과와 미달을 모두 제시하고, 남은 연구가 격차의 원인 분리임을 보여주는 편이 정확하다.

1. **학생의 격차 원인부터 확인한다.** 현재 구조를 기준으로 용량 또는 긴 범위의 패킷 관계 표현 중 한 요인만 바꾼 학생을 선정하고, 직접학습 M3와 KD M5를 함께 비교한다. ‘새 구조가 좋아짐’과 ‘증류 효과가 커짐’을 구분한다. 이미 실행한 것으로 표시하지 않는다.
2. **학습량 문제를 분리한다.** 적은 라벨 조건에서 마지막 epoch가 best인 사례와 업데이트 수 차이를 근거로, 필요하면 고정 업데이트/별도 학습 일정 비교를 사전에 정한다. 현재 예산별 최적 설정을 찾았다고 가정하지 않는다.
3. **오탐이 집중되는 서비스를 먼저 분석한다.** Drive·Crashlytics처럼 재현율과 정밀도가 엇갈리는 사례, WWW처럼 누락이 큰 사례를 나눈다. 짧은 플로우와 분포 변화의 기여는 별도 집계·검증한다. 현재 자료에서 관찰한 오류를 도메인 문자열로 우회 해결했다고 포장하지 않는다.
4. **입력 확장은 분리한다.** FLOWSTATS 추가와 mm_cesnet_v2 교체, MoE 도입은 학생 문제와 동시에 바꾸지 않는다. 관측 정보가 늘어난 이득인지 구조의 이득인지 구분하고, 전체 플로우 통계가 요구하는 관측 대기시간도 포함한다.
5. **최종 주장에는 새로운 검증을 마련한다.** 과거에 보지 않은 수집 시기·환경과 실제 추론 경로를 정해야 한다. 지금의 4·5월 수치를 반복해서 보고 최적화하면서 마지막에 ‘미사용 최종 검증’이라고 이름만 바꾸면 안 된다.

새 학습은 시작하지 않았다. 팀원은 먼저 [발표 흐름과 Q&A](midterm_handoff.md)를 읽고, 숫자 질문에는 [전체 결과표](continuation_results.md), 설계 질문에는 [연구 원장](research_record.html), 직접 실행에는 [CPU 재생 사용법](cpu_demo_readme.md)을 사용하면 된다.

### 해석의 근거 파일

- [통합 수치와 seed별 대응 차이 JSON](../../experiments/2026-10-30_midterm_restart/continuation_recovered/continuation_summary.json)
- [원격 회수 목록](../../experiments/2026-10-30_midterm_restart/continuation_recovered/recovery_complete.json)과 [A100 해제 증빙 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [로컬 후처리 상태 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)와 [완료·해석 검토 기록](../../experiments/2026-10-30_midterm_restart/continuation_recovered/completion.json)
- [CPU 예측 재생 검증 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)과 [브라우저 점검 기록 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)

모든 차이는 검증된 수치에서 산출했다. 여기서 제시한 원인 설명은 관찰과 가설을 구분하며, 수행하지 않은 통계 검정·추가 실험·외부 검증을 완료했다고 주장하지 않는다.

## 팀 공유·중간발표용 정리

다음은 약 10~12분 발표를 가정한 설명 순서다. 실제 발표 시간에 맞춰 줄일 수 있다. 모든 수치는 아래 연결된 검증 원장의 본실험 seed 5개에서 계산했다. ± 값은 seed 사이의 표준편차(SD)이며 신뢰구간이 아니다.

### 발표 본문 구성

1. **문제와 연구 질문** — 암호화된 내용을 읽지 않고 패킷 크기·방향·간격으로 서비스를 분류할 수 있는가? 정답이 적을 때 사전학습이 도움이 되는가? 작은 학생 모델에 지식을 옮겨 CPU에서 사용할 수 있는가?
2. **입력과 데이터** — 첫 최대 30패킷의 PPI만 사용한다. SNI·IP·도메인·payload·전체 FLOWSTATS는 이번 입력에 없다. 1월 학습, 2월 설정 선택, 4월 주평가·5월 시간차 평가를 분리했다.
3. **정제와 라벨 예산** — 입력이 같고 서비스가 다른 충돌을 제외하고, 정답까지 같은 중복에서는 대표를 선택했다. 기준은 30패킷 PPI다. 모든 동일 세션이나 사전학습 원천의 누수까지 없음을 증명한 것은 아니다. 클래스당 50 ⊂ 100 ⊂ 200 ⊂ 1000개의 고유 입력을 사용한다.
4. **여섯 모델의 역할** — M0는 PPI에서 계산한 통계 16개를 받는 LightGBM이다. M1은 교사 구조를 무작위 초기화해 학습하고, M2는 공개 사전학습 교사를 전체 미세조정한다. M3는 작은 CNN을 직접 학습한다. M4는 M1에서, M5는 M2에서 증류한다. M3/M4/M5는 구조·표본·초기값을 맞췄다.
5. **개발과 본실험 분리** — 개발 seed 101/102의 후보 60회에서 학습률과 공통 KD 설정을 선택했다. 이후 seed 201~205에서 고정 설정으로 대표 30회 + 후속 150회 = 180회를 학습했다. 개발 후보 60개를 동일 조건의 독립 반복 60회라고 부르지 않는다.
6. **대표 200개 결과** — 4월 Macro F1은 M2 53.771 ± 1.743%, M3 32.493 ± 0.982%, M5 32.743 ± 0.815%다. 이 점수와 seed별 대응 차이 5개로 증류가 직접학습에 추가하는 효과를 설명한다.
7. **라벨 수에 따른 변화** — 아래 표에서 특히 M2와 M5의 격차, M5−M3의 크기와 반복별 부호를 확인한다. 동일한 50 epoch이므로 많은 라벨은 더 많은 가중치 업데이트도 동반한다. 아래는 4월 Macro F1이다.

|클래스당 표본|M0|M1|M2|M3|M4|M5|
|---|---|---|---|---|---|---|
|50|29.233 ± 0.982%|40.651 ± 1.032%|42.319 ± 1.691%|19.088 ± 0.886%|18.909 ± 0.866%|19.475 ± 0.902%|
|100|31.830 ± 0.691%|46.675 ± 0.322%|49.310 ± 1.721%|26.140 ± 0.819%|26.310 ± 0.837%|26.463 ± 0.921%|
|200|34.075 ± 0.379%|50.332 ± 1.617%|53.771 ± 1.743%|32.493 ± 0.982%|32.451 ± 0.736%|32.743 ± 0.815%|
|1000|38.623 ± 0.334%|58.396 ± 1.181%|62.475 ± 0.820%|46.098 ± 0.243%|46.423 ± 0.489%|46.342 ± 0.599%|

8. **서비스 구성의 차이** — Google 포함 20개·비Google 13개·Google 계열 20개를 비교한다. 서로 클래스 목록과 수가 달라 점수 차이를 Google 포함이라는 단일 요인의 인과효과로 말하지 않는다. 각 구성 안의 M5−M3와 클래스별 혼동을 중심으로 설명한다.

- Google포함20: M2 53.771 ± 1.743%, M5 32.743 ± 0.815%; M5−M3 평균 +0.250%p, 차이가 양수인 반복 4/5.
- 비Google13: M2 80.171 ± 1.549%, M5 48.194 ± 1.684%; M5−M3 평균 +0.339%p, 차이가 양수인 반복 3/5.
- Google계열20: M2 36.625 ± 2.087%, M5 16.643 ± 1.512%; M5−M3 평균 +0.527%p, 차이가 양수인 반복 5/5.

9. **경량성과 CPU 비용** — 20클래스 교사의 파라미터 695,593개가 학생에서는 20,180개로 약 34.47배 작아진다. 파라미터 감소와 성능 유지는 별도 목표다. 원장의 CPU batch 1 중앙값/p95·처리량·저장 크기를 함께 보인다. 실측은 저장된 PPI의 처리 시간이며, 패킷 30개를 기다리는 시간은 포함하지 않는다.
10. **CPU 추론 시연** — `cpu_demo.py`로 공개 평가 PPI 한 건을 받아, 대표 seed 201 모델이 CPU에서 계산한 상위 3개 예측을 보인다. 실제 정답은 모델 입력에 넣지 않고 시연 확인용으로 분리한다. 시연 표본은 성능을 보고 고르지 않는다. 저장된 플로우 재생이며 실시간 수집을 구현했다고 말하지 않는다.
11. **결론과 후속 질문** — 증류 이득의 크기·일관성, 교사와 학생의 성능 격차, 라벨 효율과 CPU 비용을 근거로 현재 설계의 한계를 설명한다. 개선되지 않았다면 숨기지 않고 현재 설계에서 얻은 결과로 보고한다.

### 질문을 받았을 때 답할 내용

**왜 30패킷인가?**

이번 중간평가에서 정보 예산을 고정해 모델·학습 방법을 비교하기 위한 범위다. 30이 최적이라는 실험은 하지 않았다. 짧은 플로우도 포함한다. 학생은 유효 패킷을 구분하는 마스크를 사용한다.

**정답을 모델 입력에 넣었나?**

아니다. 입력은 IPT·방향·크기다. 실제 정답과 교사 확률은 학습 손실에만 쓰며, 추론할 때 학생에 교사가 필요하지 않다.

**M1/M2는 가중치만 다른 완벽한 단일 요인 비교인가?**

동일한 교사 본체 구조지만 선택 학습률도 다르고, M2는 공개 BN 통계를 유지하며 학습 가능한 affine 값을 미세조정한다. 따라서 현재 적응 정책을 포함한 사전학습 활용 비교다. 이 차이를 문서에 명시했다.

**학생이 너무 작아서 성능이 낮은 것 아닌가?**

가능한 가설이다. 현재 학생은 커널 크기 3인 CNN 3층과 마스크 평균 풀링을 사용한다. 성능 격차의 원인을 분리해 증명하지는 않았다. 용량·먼 패킷 간 관계 표현·풀링·학습 일정의 별도 실험이 필요하다.

**라벨 1000개가 유리한 것은 더 많이 학습했기 때문 아닌가?**

동일한 epoch 수에서 업데이트 수도 증가한다. 그래서 라벨 효과만을 분리한 고정 계산량 실험이라고 부르지 않고, 업데이트 수와 시간을 함께 보고한다.

**중복을 모두 없앴나?**

정의한 canonical 30-PPI 키와 원본 ID를 기준으로 정제·분리했다. 전체 세션·기기·수집망·공개 사전학습 원천의 중복까지 배제했다는 증거는 없다. 평가 데이터의 겹침·비겹침 결과도 별도로 보존한다.

**4·5월은 완전한 새 데이터인가?**

이번 설정 선택에는 쓰지 않았으나 과거 실험에서 본 적이 있는 월이다. 따라서 시간차 재평가이며 완전히 미사용한 외부 최종 검증으로 포장하지 않는다.

**Google을 넣으니 어려워졌다는 결론인가?**

서비스별 혼동과 구성별 결과는 보일 수 있다. 클래스 수·목록·난이도도 달라 Google 포함 여부만의 인과효과라고 단정할 수 없다.

**KD가 통계적으로 유의한가?**

seed 5개의 대응 차이와 표본 표준편차를 그대로 제시한다. 작은 평균 차이를 유의성 검정 없이 확정적인 우위라고 부르지 않는다.

**50개/클래스만으로 연구 전체를 수행했나?**

50개는 해당 모델의 fitting 예산이다. 후보 정제에는 더 많은 라벨을 읽었고 개발 설정은 대표 200개 조건과 2월 검증으로 골랐다. 연구 전체의 라벨 접근량과 모델 fitting 예산을 구분한다. 이번 KD에는 추가 무라벨 풀을 쓰지 않았다.

**왜 2월보다 4월 점수가 많이 낮은가?**

2월은 균형 검증이고 4월은 자연 빈도 평가이며 checkpoint 선택 여부도 다르다. 시간 변화·표본 구성·검증 선택의 영향이 섞여 있다. Macro-F1도 정밀도를 통해 클래스 빈도의 영향을 받으므로 점수 차이를 전부 시간 변화로 설명하지 않는다.

**성능 보존 목표를 달성했나?**

대표 200개 조건에서 M2 대비 M5의 Macro-F1 손실은 평균 21.028%p로 2%p 이내 목표에 미달했다. 34.47배 파라미터 축소와 지정 CPU batch1 지연 약 8.86배 감소는 확인했지만 성능 보존까지 성공했다고 말하지 않는다.

**왜 M0는 CPU인가?**

LightGBM도 정답으로 분기와 잎 값을 학습하는 모델이다. 기존 비교 설계대로 CPU 1스레드를 사용하고 신경망은 A100에서 학습했다. 모든 최종 모델의 배포 비용은 같은 로컬 CPU 1스레드 규칙으로 별도 측정한다.

**실시간 서비스 분류나 이상탐지까지 완성했나?**

이번 증거는 공개 데이터의 폐쇄형 서비스 분류와 저장 PPI의 CPU 재생이다. 실제 패킷 수집·전처리 동일성·미등록 서비스·이상탐지·새 네트워크에서의 일반화는 별도 검증 대상이다.

**연결이 끊긴 실험은 어떻게 처리했나?**

회수하지 못한 PID 2161의 학습 30회는 완료 수와 성능표에서 제외하고 동일 설정으로 재실행한 기록을 남겼다. 검증된 원본 ZIP과 예측·체크포인트를 가진 실행만 집계했다.

### 마지막 장에서 말할 결론

“정제한 동일 입력과 라벨 예산에서 M0~M5를 5회 반복 비교했습니다. 사전학습을 활용한 교사의 평균 성능은 높았지만, 현재 학생에 KD를 더한 이득은 작았습니다. 대표 조건의 M5−M3은 +0.250%p이고 교사와의 격차는 21.028%p입니다. 학생의 크기와 지정 CPU 지연은 줄였지만 성능 보존 목표는 아직 달성하지 못했습니다. 다음 단계에서는 학생의 표현·용량·학습량 중 어떤 요인이 격차를 만드는지 분리하겠습니다.”

이 결론은 실패를 숨기거나 프로젝트 전체를 실패로 단정하지 않는다. 미달한 목표와 다음에 검증할 질문을 연결한다. Google 내부 혼동, 라벨 곡선, 겹침 support, 학습곡선과 측정 한계는 [상세 해석](continuation_interpretation.md)에 정리했다. 원인 분리나 새 구조 학습은 아직 실행하지 않았다.

### 완료와 남겨둔 범위

검증 완료: 개발 학습 60회, 본실험 학습 180회(대표 30 + 후속 150), 4·5월 모델 평가 360회, 본실험 모델 180개의 CPU 비용 측정. CPU 시연의 실제 점검 여부는 `cpu_demo_verification.json`을 따른다. 채널 제거·다른 학생 구조·mm_cesnet_v2/FLOWSTATS·MoE·새 외부 데이터/실시간 수집은 선택 또는 후속 범위로 남긴다. 발표 파일 제출·학교 양식 적용·실제 발표 시간 확인은 별도다.

근거: [통합수치JSON](../../experiments/2026-10-30_midterm_restart/continuation_recovered/continuation_summary.json) · [전체설계와검증원장](research_record.html) · [CPU시연사용법](cpu_demo_readme.md).

## 2026-10-31 추가 진단 — Google 서비스 같은 월 미사용 플로우 평가

사용자 요청: 평가 월이 학습 월보다 늦어 Google 세부 서비스 성능이 낮아졌는지 확인하기 위해 같은 월의 학습 미사용 데이터를 즉시 평가한다.

기존 Google-only 20서비스·클래스당200개·M0~M5×5seed의 30개 체크포인트를 그대로 사용했다. 추가 학습·새 모델 선택은 0회다. 대상5seed의 학습 입력 합집합 및 모든 준비된 개발·검증 표본과 source ID/정확한30PPI가 겹치는 기록을 제외했다. 1월 남은426,842개 중 서비스당최대1,000개를 결과 확인 전에 고정하여14,344개를 평가했다. 4·5월은 기존 예측파일을 재사용했다. 신경망도 로컬CPU에서 추론만 했으며 A100 재연결은 하지 않았다.

월별 서비스 구성 비율을1/20로 통일한 Macro-F1(5seed평균)은 다음과 같다. 기존 보고서의 자연 비율Macro-F1과 구분한다.

|모델|1월 같은 월(%)|4월(%)|5월(%)|
|---|---:|---:|---:|
|M0|50.548|29.664|28.242|
|M1|68.982|47.848|46.261|
|M2|74.559|51.678|50.219|
|M3|43.836|27.422|26.867|
|M4|43.112|27.527|27.107|
|M5|44.183|27.937|27.366|

M2의 동월−4월 차이는+22.881%p이며5seed모두 같은 방향이다. 중복·충돌 정제 후에도75.567%대51.753%로 유지됐다. 4월비겹침의서비스비율로 모두환산하면1월51.323%,4월36.844%,5월36.648%다. 월별 분포 차이의 영향을 시사하지만 시간만의 인과효과, 세션독립성, 처음개봉한테스트를 입증하지 않는다. 대상모델에는 미사용이나 다른구성모델에 쓰였을 수 있다. 학생M5의 동월44.183%와 교사74.559%차이도남아있다.

원본캐시·코드·체크포인트·기존예측해시검증, 30모델×400표본 CPU재생라벨100%일치, 독립sklearn재가중Macro-F1계산일치까지확인했다. 느린batch256교사추론을중지하고batch1로재개한운영기록도보존했다. 기존180학습/360월간평가/180CPU비용측정집계는변경하지않으며 이번30개동월평가를별도진단으로분리한다.

- [추가 진단 보고서 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [자세한 해석 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [결과 확인 전 설계·표본 기록 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [전체 seed 결과·혼동행렬 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [검증 기록 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)

### 같은 날 후속 요청 — 다른 서비스 구성으로 확장

사용자 요청 “다른 서비스들도 한번 진행해봐”에 따라 Google포함20개와 비Google13개를 서비스당200개 조건으로 추가평가했다. 구성마다 기존M0~M5×5seed30개, 총60개저장모델의1월추론을 수행했다. 추가학습0회이며 기존Google전용30개결과는재실행·변경하지않았다. 첫최대30PPI·고정가중치·동일월제외규칙·무작위표본seed20261031·서비스당최대1000개를 유지했다. 각모델의학습5seed합집합및모든준비된개발/검증입력과정확히겹치는입력/ID는0개다.

|구성|1월 평가 표본|M2 1월/4월/5월(%)|M5 1월/4월/5월(%)|
|---|---:|---|---|
|Google포함20|17,257|77.01 / 62.85 / 62.12|50.88 / 39.60 / 39.74|
|비Google13|12,838|92.50 / 90.26 / 89.54|63.72 / 60.50 / 60.40|

지표는구성내서비스비율을1/C로통일한Macro-F1의5seed평균이다. 기존자연비율Macro-F1과다르다. M2의동월−4월차이는Google포함+14.157%p,비Google+2.233%p로,Google전용+22.881%p보다작다. 클래스수13/20및정답구성이다르므로Google유무만의인과대조가아니다. 비Google M5를4월서비스비율로환산하면1월48.31%,4월48.25%,5월48.26%로월별차이가매우작다. Meta학생은동월에도Graph Recall31.88%,Instagram57.00%로한계가남으며서비스마다시간차양상이다르다.

두구성모두원본캐시·코드·체크포인트·기존예측해시및학습입력문맥을검증했다. Google포함재생12,000건,비Google7,800건모두기존저장예측과라벨100%일치했다. 새30모델×2구성각각에서sklearn로균등/4월비율F1과Recall을독립재계산하여일치확인했다. 이번60개동월평가는사후진단집계이며기존본실험180학습·360월간평가·180CPU비용측정집계를대체하지않는다.

- [세 구성 통합 보고서 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [통합 해석 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [Google포함 전체 결과 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [비Google 전체 결과 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [발표용 통합 그래프 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)

### 2026-11-01 — 33개 서비스 패킷·모델 실패 원인 진단

사용자가 실제 서비스별 흐름을 직접 조사하고 현재 모델이 놓치는 특징을 확인하도록 요청했다. 로컬 XS HDF5 12개월 1,000만 행을 스캔하여 최종33개 서비스의 6,267,394개 흐름과 저장된 유효 PPI 156,077,809개를 집계했다. 순서가 있는 패킷은 첫 최대30개뿐이며, 그 이후는 전체 플로우 카운터·지속시간·히스토그램만 있다. 원본과 기존 PPI 캐시의 대상 행을 전부 대조했다. 모든 실제 후반 패킷을 개별 확인했다는 주장은 하지 않는다.

67개 특징의 서비스×월 분포, 패킷 위치별 분포, 정확한 입력 충돌, 길이·첫 크기·도메인 계열별 성능, 교사/학생의 동일 입력별 정오답을 연결했다. 기존270개 혼동행렬과954개 서비스 집계의 support/Recall이 일치했다. 학습200/class 조건의 M2/M3/M5×3코호트×5seed=45개 고정 체크포인트를 자기 학습 표본에서 CPU 추론만 재평가했고, M2/M5 seed201의6개 모델은 서비스당100개 고정표본으로 입력 민감도를 조사했다. 추가학습0회, GPU 재연결0회이며 기존180fit/360월간평가/180CPU비용 집계에 합산하지 않는다.

Google 전용의 학습 정확도는 M2 92.55%, M3 49.16%, M5 49.25%다. 따라서 학생 격차를 시간차만으로 설명할 수 없다. 1월 서비스 평균Recall은 M2 74.36%, M5 46.13%, 4월은51.15%,29.60%다. 지표는 이 절에서Recall이며 기존Macro-F1과 구분한다. 입력 변형에서 학생도 IPT·순서에 강하게 반응했다. 실제 구조는 pooling 전 교사 최대19패킷/학생7패킷 국소 수용 범위이며 학생은30개 전체의 국소 점수를 평균한다. 크기32B 반올림에 교사는 민감하고 학생은 훨씬 덜 민감했다. 원인이 인코딩/최적화/구조 중 무엇인지 인과 분리한 것은 아니다.

Hangouts/Meet는 원본 meetings.googleapis.com 비중이1월82.1%에서4월19.4%로 바뀌었고 meet 계열이79.0%로 늘었다. 4월 전체62개, 하위12/49개 수준이므로 해석을 제한한다. Photos는 첫 크기와 도메인 구성이 함께 바뀌었으며 같은 하위 계열 안에서도Recall이 하락했다. IMA SDK/reCAPTCHA는 같은 도메인에서도 큰 변화가 있었다. 전체 히스토그램의 단일 특징 탐색은 일부 혼동쌍에서 유망하지만 Drive/Docs 등에는 제한적이었다. 사후43쌍AUC는 다중클래스 개선실험이 아니다.

33서비스의 개별해석,197개 실제사례의 모든 저장패킷 숫자,33개 서비스그림,6개 요약그림,33개 학생logit의 정확한 국소합 분해를 보존했다. 원본SNI·IP는 내보내지 않았으며 공식도메인계열만 진단에 사용했다. 기존 모델 입력에 도메인을 추가하지 않았다. 확정 관측과 가설을 구분하고 학생적합→인코딩/수용범위 대조→전체통계 추가→시간·하위유형 평가 순으로 후속 검증을 제안했다.

- [패킷·모델 실패 진단 보고서 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [분석 텍스트 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [원본 범위·해시·67특징 정의 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [추론·체크포인트 검증 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [보고서·근거파일 검증 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)

### 2026-11-01 — 실제 PPI 숫자열에 초점을 맞춘 후속 관찰

사용자가 서비스별 실제 PPI 값을 직접 확인하고 학습 방식에 연결해 달라고 요청했다. 앞선 원본-캐시 전수 일치 결과를 재사용하여33서비스의2025년1·2·4·5월2,129,964개 흐름을 첫30PPI만으로 조사했다. 서비스·월 내 정확한30×3입력을1회씩 세면2,084,435개다. 월간 중복이나 세션 상관을 제거한 독립표본수는 아니며 라벨 간 동일 입력도 유지했다. 원본 빈도와 중복1회 빈도를 별도로 보존했다.

서비스별1·4월의 상위2개 거친 초기 유형에서 실제132개를 추출하고, 공통 초기 패턴 이후 크기 비교를 위해 조건부 중앙값에 가장 가까운 실제20개를 추가했다. 사례152개의 모든 저장PPI·원본ID,33서비스 쌍 그림과6개 비교 그림,28특징과28규칙 및 실제 사례에서 찾은8개 숫자패턴을 기록했다. 숫자패턴은 사후 정의했고 모든 월을 이미 살펴봤으므로 독립 검증 성능으로 주장하지 않는다.

TikTok은11~30번에서 정방향 인접 크기의 합1320B인 창이3개 이상 반복되는 비율이31.23/37.59/28.17/34.55%(1/2/4/5월)였다. 실제1055+265,570+750형태를 확인했다. 조사한 다른32서비스에서는 이 규칙이0건이었다. Private Relay의짧고 동일크기·약5초간격 반복과Discord의초기7개 숫자열도 일부 유형에서 월간 재등장했다. 서비스 전체나 다른 환경의 고유서명이라는 뜻은 아니다.

Meta 공통12패킷 초기형태 안에서14번째DIR×SIZE 중앙값은 Graph255→241B, Web752→717B, WhatsApp207→492B였다(1월→4월). Spotify/Unity 공통초기유형에서는893→926B와165→161B였다. Google 여러서비스는 -613/(-121또는-137)/+31/(+50또는+54)를 공유하며 그 다음 크기에 일부 조건부 차이가 있지만 분포도 겹쳤다. 초기형태가 비슷하다고 모든 PPI가 같은 것은 아니며, 한 실제사례의 숫자만으로 전형성을 주장하지 않았다.

새 학습·GPU연결·모델추론은0회다. 실제 오답과 새패턴의 인과연결은 미검증이다. 세부크기 인코딩,국소순서와뒤문맥,방향별/구간별요약,인접크기관계,긴IPT표현을 각각 대조할 후보로 제시했으며 개선을 확정하지 않았다. Docs/Translate등에는 강한 고유패턴을 억지로 부여하지 않았다. 기존180fit/360평가/180CPU비용 집계는 변경하지 않았다.

- [서비스별 실제 PPI 패턴 보고서 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [텍스트판 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [직접 찾은 숫자패턴의 월별 원본/중복1회 빈도 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [조건부 크기 분포 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [실제 사례·수치·링크 확인 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)

### 2026-11-01~02 — 학생 단서 활용과9개 개선의 실제 대조

사용자가 앞선 진단·PPI 패턴 제안을 즉시 적용하고 기존 학생과 비교하도록 승인했다. Google 전용20·비Google13·Google 포함20, 서비스당200개, seed201~205를 고정했다. 기준 학생 재학습+9개 변경(150epoch, SIZE 임베딩, RF19, 위치 pooling, PPI 요약, 전체 플로우 통계, 인접 크기 관계, 구간·방향 요약, 긴 IPT 요약)의150fit와 검증으로 선택한 임베딩의KD15fit, 총165회CUDA FP32 학습을 완료했다. 선택·마지막 가중치와9,750epoch 기록, 원본 입력과 결과ZIP을 회수하여 전체/내부SHA256·CRC·경로·ID·초기값·선택 규칙·교사 대응을 확인했다. A100은 실제 로컬 보존과 검증 후 해제했으며 비연결 화면과 시각을 남겼다. 전송 중 세션 소실과 초기 해시 순회 순서 오류는 각각학습0회 상태에서 발생했고, 실패 기록을 별도 보존했다.

새 모델165개×1·4·5월=495건 월별 평가는 로컬AppleGPU(MPS)로 완료했다. 기존과 같은 평가 행이며 각 모델·월에서 작은CPU 출력 대조를 수행했다(최대logit차1.90735e-5). 기준15모델의 선택가중치는 기존M3와 완전히 같았다.8,628,380개 모델·행 예측 중2개만 이전 저장 예측과 달랐고 해당상위logit차는3.58e-7/4.77e-7로 거의동률이었다.100%예측일치라고 표시하지 않았다.27개 모델·월에서sklearn로 일반/균등가중F1을 독립계산하여 일치했다. 원본M0~M5 참조270건을 재집계했고, 기존180fit/360월별평가/180CPU비용 집계에 새 실험을 섞지 않았다.

|조건|Google 전용4월|비Google4월|Google 포함4월|
|---|---:|---:|---:|
|기준 학생|27.42|60.01|39.30|
|150epoch|36.67|71.03|47.70|
|SIZE 임베딩|33.81|75.31|44.41|
|SIZE 임베딩+KD|34.90|76.16|45.07|
|전체 플로우 통계|42.06|71.38|50.07|

서비스균등가중Macro-F1(%),5seed평균이다.150epoch·임베딩・RF19・위치pooling・전체통계의4월 개선은 세 구성 모두5seed에서 같은방향이었다. PPI 단순요약·긴IPT 분기는 평균개선이 작고 일부seed가 낮았다.150epoch는스케줄길이도바뀌며,임베딩/위치pooling은파라미터수가증가한다. 전체통계는관측정보를늘리므로조기30패킷조건과관측대기시간을구분했다. 비Google 검증2,600개 중정확한학습PPI와같은4개를새조건공통으로제외해2,596개를사용했다. Google전용3,933개/혼합4,000개는그대로다. 원래M2교사에남는검증조건한계도명시했다.

패턴별4월 재현율에서Spotify 공통초기형은기준44.11→전체통계88.26%,Graph Meta초기형은35.79→150epoch84.25%/위치pooling83.04%였다. Google-www 공통초기형은1.31→전체통계17.05%로여전히낮았다. TikTok 인접합유형은기준부터95.05%,PrivateRelay 주기형은100%라모든단서를놓쳤다고주장하지않는다.33서비스의조건별수치와모든후보를보존했다.

별도입력민감도진단30모델×원본/32B반올림=60건을수행했다. 모든유효SIZE를최대16B바꾸면임베딩예측의약94%가바뀌고하위표본F1은3.5~4.5%로급락했다. 기준학생예측변경률은1.2~1.4%였다. 전체유효패킷의97.4~99.0%를동시에변형한시험이며단일패킷변경이나실제월간변화와같다고해석하지않는다. 미학습SIZE범주는변형패킷의1.4~3.1%로,미관측크기만의문제로단정하지않는다. 원본성능개선과세밀한크기에대한의존·취약성을함께기록했다.

학습모델165개CPU1스레드비용도측정했다.20클래스기준batch1은기준0.0395ms,150epoch0.0397ms,임베딩0.0466ms,RF190.0984ms,전체통계0.0443ms였다. 모델메모리상주forward이며사전계산통계추출·수집대기·I/O는제외한다. 학습예산확대는추론구조를바꾸지않았고,같은파라미터수의RF19도더느릴수있었다.15종그래프를PNG/SVG/PDF로저장했다.

모든월과패턴을이미본뒤만든사후개선비교라독립최종검증으로주장하지않는다.5seed가같은평가행을공유하며,한서비스형태의개선이특정패킷값의인과효과를증명하지않는다. 임베딩+연속크기,크기변형학습,조합실험,새시점확인은후속후보이며이번에학습하지않았다.

- [학생 개선 비교 보고서 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [수치 해석과 한계 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [고정 실험 설계 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [모든 조건·월·seed 차이 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [33서비스와혼합조건 상세 수치 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [원본 ZIP과165모델 검증 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [독립 지표·기준 재현 확인 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [A100 해제 증거 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)

## 2026-11-02: 관측 범위·Google PPI·배치·1-NN·학생 확대·특징 증류·prefix·샘플링·SIZE 견고성 후속 비교

사용자의10개 후속 요청을 고정 대조로 수행했다. Google 내부20서비스26조건×5seed=130fit, 비Google13과Google포함20은각7조건×5seed=70fit, 합계200회CUDA A100 FP32 학습이다. 서비스당200개,seed201–205,2월검증 선택을 유지했다. 기본50epoch이며 명시된150epoch·업데이트수맞춤 조건만 예외다. 추가 조합 탐색은 하지 않았다. 기존중간180fit 및11월1일165fit와별도로 집계한다.

200개선택모델×1·4·5월=600건월별평가, 200개×1·4월×6입력조건=2,400건견고성평가를완료했다.6조건에는원본이포함돼변형만세면2,000건이다. 모델별CPU추론비용200개와별도1-NN75건도완료했다. 새신경망학습은GPU,회수후월별·교란추론은AppleMPS,CPU는출력대조·추론비용측정에사용했다. 전체/내부SHA256·CRC·경로·입력ID·초기값·교사연결·학습예산·선택체크포인트검증200/200통과후원본4ZIP을로컬보존하고A100을2026-11-02 02:00:57KST에해제했다. 비연결화면·시각·무결성기록을보존했다.

실행중임베딩초기값의로컬/Colab수치차이가다음모델첫업데이트전에발견돼멈췄다. 완료한기준5fit를보존하고고정초기값파일을전송하여195fit를이어갔다.초기값·기존결과·절대시간상한은바꾸지않았다.회수검증시교사캐시index에후기설명1키가덧붙은것도검출했다.변경본을별도보존하고원래SHA확인된입력ZIP의정확한index바이트를복원했으며,캐시5파일·실제교사값은변경되지않았다.검증규칙을완화하지않고검증을통과했다.두사건모두원본실패기록과수정이력을남겼다.

|Google 내부20서비스|1월 F1|4월 F1|5월 F1|
|---|---:|---:|---:|
|기준 학생|43.84|27.42|26.87|
|SIZE임베딩|52.49|34.03|32.16|
|연속+임베딩 hybrid|52.93|32.99|31.53|
|hybrid+크기증강150epoch|61.14|37.93|38.10|
|CNN폭4배|57.83|39.73|39.19|
|첫30PPI+첫30요약37통계|53.28|37.87|36.79|
|hybrid 계층적KD|54.95|34.30|33.43|

수치는서비스균등가중Macro-F1(%)의5seed평균이다.첫30통계만으로4월+10.45pp여서전체FLOWSTATS의이득을31번째이후정보로만설명할수없다.원본에는31번째이후의순서PPI가없으므로전체PPI비교는미실행이다.전체통계와의차이는관측시간·클리핑·exporter정의도포함한다.

Google1·4·5월480,691플로우집계와고정균형27,295표본의prefix분석,실제정오답180개·조건부74개숫자검토를기록했다.1월DIR·SIZE공유율은첫4개83.3%·첫30개4.7%였다.Crashlytics–Ads의조건부7번째signedSIZE구분AUC는.968→.527로월간약화했으나Calendar–Photos는.972→.965로유지됐다.값을유지하면서단서위치가이동한서비스와IPT가두배씩늘어나는공통오류군도확인했다.헤더없는backoff추정과작은support의한계를명시했다.전체48만흐름을사람이눈으로읽었다거나패킷31+·payload를확인했다고주장하지않는다.

batch64는50epoch에서4월31.45%지만업데이트를1,600으로맞추면25.94%였다.batch256은50epoch23.52%,1,600updates28.90%였다.배치효과와업데이트·노출량의차이를분리해기록했다.계층KD는pooledKD보다4월+0.10±1.48pp·5월+0.60±1.35pp,각3/5seed만양수여서확정우위를주장하지않는다.앞8개마스킹4월27.63%는기준27.42%와차이가작고실제handshake식별제거가아니다.window20은고정첫20보다낮았고,균등15는첫15보다4·5월에서높지만1월은낮았다.무작위15증강은낮았다.

공개동결448D+1-NN의Google4·5월은58.99/57.28%,미세조정M2특징1-NN은56.52/55.44%,M2분류기참조는51.68/50.22%였다.1-NN은4,000개라벨지원표본을검색하며1개표본학습이라는뜻이아니다.공개동결만다운스트림미세조정없는전이평가다.CPU공개1-NN질의약0.374ms·지원벡터6.836MiB추가이며사전학습표본의개별독립성까지입증하지않았다.

SIZE임베딩은작은크기변형에민감했다.Google1월균형probe에서임베딩원본52.45→32B반올림3.65%,한패킷±16B는49.51%였다.hybrid만으로해결되지않았고증강150epoch는61.58→반올림58.88%로완화됐다.그러나비Google같은모델은원본82.57→반올림55.87%여서모든체계적변형에강한것은아니다.연속SIZE폭4CNN은Google원본58.43→반올림58.46%로유지됐다.SIZE제외는원래4월성능을27.42→22.35%로낮췄다.합성변형의프로토콜가능성·라벨보존은검증되지않았으며실제월간평가와구분한다.증강없는hybrid150대조가없어학습량·cosine일정효과와증강효과를완전히분리할수없다.

Google기준CPUbatch1forward0.0480±0.0183ms,폭4배0.0783±0.0012ms,hybrid증강150은0.0476±0.0014ms였다.파라미터는20,180/301,844/32,956개다.첫30통계모델은준비된통계에서forward0.0444ms지만통계추출부터측정하면0.3492ms였다.1스레드·2라운드·batch1/128을측정했으며수집대기·I/O와전체RSS는미측정이다.현재환경의배치별backend효과및시간변동을무시한속도우위를주장하지않는다.

모든월을이미관찰한후속탐색이며새로운블라인드최종검증이아니다.200fit/600평가/2,400입력조건/75NN/200CPU완료와서비스분류문제해결을구분했다.학습곡선·선택규칙·서비스별precision/recall/F1·혼동·seed별차이·실제PPI사례·실패기록·환경·원본예측을보존하고11종그림을PNG/SVG/PDF로생성했다.

- [후속 실험 통합 보고서 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [열 가지 질문의 해석과 비용·한계 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [Google20서비스 실제 PPI 분석 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [1-NN 평가 상세 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [학습곡선·선택모델 분석 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [고정 설계 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [전체 결과·대응비교 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [회수 무결성 검증 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [A100 해제 증거 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)


## 2026-11-02: 7시간 데이터·epoch 확대 요청 — 학습 시작 전 실패

이전 후속200fit와 별도로 최대48fit·최대500/1,000epoch의 새 큐와7개 확대 데이터 조건을 준비했다. Google 내부 학습 후보는4,000/18,778/61,941/194,325개로 확대했고, 클래스별 수를 맞춘1~3월61,941개 조건과비Google·혼합 조건도 준비했다. 이는 **준비 수량이며 학습 실적이 아니다**.

Colab 업로드 도구 호출이26,722.7477초 동안 반환되지 않아02:27:32~09:27:32KST의7시간 기한을 넘겼다. A100 환경 확인 셀만 실행했고 **새 본학습0회·smoke업데이트0회·월별평가0건·CPU비용0개**다. 업로드 완료·원격SHA검증도 확인하지 못했다. 업로드 전에 독립 감시를 설치하지 않은 실행 순서상의 잘못을 기록했다. 제어를 돌려받은 뒤 추가 학습은 시작하지 않았다.

Colab의 활동 없음/최대 길이 도달에 따른 자동 종료 알림을 확인하고 ‘다시 연결 A100’ 비연결 화면을 보존했다. 정확한 종료 시각·GPU 과금 시간은 미확인이다. 이번 임시 잠자기 방지PID83246도 종료된 것을 확인했다. 입력ZIP·설계·코드는 로컬 보존했으며 기존 완료 결과와 혼합 집계하지 않는다.

- [확대 캠페인 준비·실패 보고서 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [실행 사실 기록 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)
- [런타임 자동 종료 증거 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts)


## 18. 계획서 대비 변경·진행 상태

| 계획서 항목 | 현재 상태 | 설명 |
|---|---|---|
| PPI 전용, SNI/IP 제외 | 구현·연결 점검 | first≤30, short 포함, 고정 변환 |
| 교사 사전학습/전이 | 구현·개발 완료 | pooled448 경로 확정; 원래 wrapper 크기를 현재 교사 크기로 인용하지 않음 |
| 학생 약20,180 설계 | 실제 구조 확인 | 기본 CNN 하나 확정, 실측 param20,180 |
| 서비스 빈도순20 | 사용자 선택으로 조정 | Google 포함 명시목록·정제후≥1000, 나머지구성은후속 |
| 라벨50/200/1000 | 100추가 승인 | 중첩50/100/200/1000, 200개발부터 |
| 학습 기반 정규화 통계 | 고정 변환 채택 | 데이터 추정 scaler 없이 상수 사용 |
| M0~M5 본 실험·5회 | 대표30+후속150=180fit 검증 완료 | 혼합20의50/100/200/1000 및 비Google13·Google전용20의200개 |
| 4·5월 성능 | 360평가 회수·지표 검증 완료 | 전체·겹침·비겹침·공통미관측 및 클래스별 결과 보존 |
| CPU 지연·처리량·메모리 | 본모델180개 측정·검증 완료 | 동일로컬CPU1·FP32 프로토콜; 실시간수집대기는 제외 |
| 채널 제거 기여도 | 선택 확장 | 기본 결과·라벨 확장 뒤 여유시 |
| CPU 시연 | 저장공개PPI 재생 구현·예측·브라우저 점검 | 실제네트워크수집시연은 별도검증 |
| 이상 탐지/미등록 서비스 | 이 비교로 입증하지 않음 | 폐쇄형 서비스 분류 범위를 넘어섬 |

과거 계획서의90회는 3개 라벨 예산×6모델×5회였고, 현재4개예산은120회다. 개발 탐색·속도 점검까지 포함한 전체 비용은 별도다. 일정은 계획서상11/10 자료 제출·11/11 중간발표이나 최신 학교 공지와 일치 여부는 아직 확인되지 않았다. 발표 약3일 전 새 탐색을 멈추고 분석·자료를 우선한다는 운영 원칙은 유지한다.

## 19. 질의응답 — 근거까지 연결한 답변

### Q1. 왜 굳이 사전학습과 증류를 둘 다 쓰나요?
공개 가중치가 적은 목표 라벨에서 교사에 도움이 되는지와, 그 이점이 작은 모델에도 전달되는지는 별개의 질문입니다. M1/M2로 교사 활용 효과를 보고, M3/M4/M5로 학생의 직접학습·증류·사전학습 교사 증류를 구분합니다. 증류가 반드시 좋다는 전제는 두지 않습니다. **근거: §1·7·11.**

### Q2. 모델 여섯 개가 구조 여섯 개인가요?
아닙니다. 트리 한 계열, 큰 교사 한 구조의 두 학습 방식, 작은 학생 한 구조의 세 학습 방식입니다. 학생끼리는 같은 구조·초기값·표본·일정을 맞춥니다. **근거: §7·10, architecture snapshot.**

### Q3. M0도 학습하나요? 왜 CPU인가요?
LightGBM은 실제 정답으로 분기 기준과 leaf 값을 학습합니다. 현재 CPU 1스레드로 학습하는 트리 기준선이고, 신경망 학습은 A100을 사용합니다. 학습 장치와 최종 CPU 추론 비용 측정은 구분합니다. **근거: §8·15, training.py의 fit_m0.**

### Q4. 교사와 학생에 똑같은 데이터를 주었나요?
같은 cohort·seed·budget의 실제 ID·정답·관측 정보를 공유합니다. 다만 표현 방식은 다릅니다. 교사는 embedding과 residual CNN, 학생은 고정 변환과 작은 CNN, M0는16개 통계를 사용합니다. 같은 관측 정보를 제공했다는 말과 내부 표현이 같다는 말은 다릅니다. **근거: §6~11, 입력·라벨 해시.**

### Q5. 정답이나 교사 예측을 입력에 붙여 정답을 누설한 것 아닌가요?
추론 입력은 PPI 또는 PPI 통계뿐입니다. 정답과 교사 확률은 학습 손실에만 사용합니다. 학생을 배포할 때 교사나 정답은 필요하지 않습니다. **근거: models.py의 forward와 kd_loss, §6·11.**

### Q6. 200개 라벨만 사용했다고 할 수 있나요?
클래스당200개는 개별 모델 fitting의 예산입니다. 정제에서는1월 후보 전체 라벨을 읽었고,2월 검증과 대표200개 조건의 개발 과정도 사용했습니다. 연구 전체 라벨 접근량과 개별 학습 예산을 나누어 공개합니다. **근거: §4.2, 각 manifest의 label_access_rows.**

### Q7. 학습 데이터는 균등한가요? 평가는요?
각 fit은 클래스당 같은 수의 고유 PPI를 추출합니다. 검증은 최대200개/서비스로 고정하고 부족하면 전량 사용합니다. 주 평가는 월별 원래 빈도를 유지합니다. Macro-F1과 Accuracy·support를 함께 보고합니다. **근거: §4·14, 서비스별 표.**

### Q8. 중복을 제거했으니 누수가 완전히 없나요?
동일 source ID의 분할 중복과 canonical PPI의 학습 중복을 확인했습니다. 하지만 동일 세션이 다른 ID로 다시 수록되었는지, 공개 사전학습 원천과 겹치는지까지 보장하지는 않습니다. 자연 발생 PPI 재등장은 All에 남기고 겹침/비겹침으로 분해합니다. **근거: §5.**

### Q9. 왜 평가에서 학습과 같은 입력을 남겼나요?
다른 시점의 별개 flow가 같은 PPI를 보이는 현상도 실제 분포의 일부이기 때문입니다. 같은 원본 기록의 복제 누수는 막되, 자연 반복을 포함한 성능과 미관측 입력 성능을 함께 보고합니다. **근거: D06, §5.1.**

### Q10. 학습 라벨 충돌을 없앤 것은 유리한 데이터만 고른 것 아닌가요?
분포를 바꾸는 설계 선택임을 인정합니다. 제한된 PPI만으로 구분할 수 없는 대응을 학습에서 격리하되, 규칙은1월 안에서 고정하고 제외 건수를 공개합니다. 평가의 충돌 기록은 삭제하지 않습니다. **근거: §5, curation audit.**

### Q11. Google 서비스가 어려운 원인을 입증했나요?
아직 원인을 하나로 입증한 것은 아닙니다. 유사 패턴·라벨 범위·표본 수·시간 변화 등 여러 가능성이 있습니다. 서비스별 혼동과 조건 통제로 범위를 좁힙니다.13클래스 대20클래스의 총점 차이를 Google만의 효과라고 설명하지 않습니다. **근거: §4·14.**

### Q12. M1은 모든 가중치가 랜덤인가요?
공개 학습 checkpoint는 사용하지 않습니다. 다만 공식 모델의 데이터 비의존 PLE 초기화는 유지하므로 ‘전부 무작위’라고 설명하면 부정확합니다. **근거: §9.1, official_model_factory.py.**

### Q13. M2는 전체 미세조정인데 BN은 왜 고정인가요?
BN running 통계와 학습 파라미터는 다릅니다. backbone·embedding·분류기·BN affine·GeM p는 학습하고, running mean/variance만 유지합니다. M1과 다른 정책이므로 결과를 초기 가중치 하나만의 효과로 주장하지 않습니다. **근거: §9.2.**

### Q14. 교사 파라미터 수가 논문·계획서와 왜 다른가요?
공개256 wrapper, refinement를 포함한 backbone, 이번 pooled448 분류기는 서로 다른 경로입니다. 현재는 refinement와 neck을 빼고20클래스 head를 붙여695,593개입니다. 어느 경로를 셌는지 모듈과 계산을 남겼습니다. **근거: §9, architecture snapshot.**

### Q15. 학생은30패킷의90개 숫자를 MLP에 넣는 모델인가요?
아닙니다. 채널3×패킷 축30인1D CNN으로 순서를 처리합니다. 세 층의 convolution으로 국소 패턴을 추출한 뒤 유효 위치의 평균을 구해 고정 크기 표현을 만듭니다. **근거: §10.**

### Q16. 50epoch면 충분히 수렴했나요?
50은 개발 출발 후보입니다. 회수 후 선택된 신경망10fit의 곡선을 검토했고, 모두50보다 이른 시점에서 best를 얻었습니다. 50을 유지할 근거는 있지만 cosine 일정의 끝에서 평탄해졌다는 사실이 전역 수렴을 증명하지는 않습니다. 본 실험용50epoch는 main_frozen.json에 확정했으며, 불리한 모델만 나중에 연장하여 같은 조건 비교로 보고하지 않습니다. **근거: §12·회수 후 분석 메모.**

### Q17. KD 설정을 유리하게 많이 탐색한 것 아닌가요?
KD에는 추가 탐색 비용이 있으며 숨기지 않습니다. 총36개 KD fit을2월에서 평가하고 M4/M5 공통 조합을 선택합니다. M3에도3개 LR×2개 seed를 제공하지만 총 탐색 횟수가 모두 같은 것은 아닙니다. **근거: §12·13.**

### Q18. 5회 반복이면 독립 검증이 충분한가요?
5회는 표본·초기화 변동을 관찰하기 위한 반복입니다. 공통 검증과 같은 평가 기간을 쓰므로 새로운 환경5개를 검증한 것과 다릅니다. 반복별 차이와 표준편차를 보이고, 독립된 새 수집 검증이 아님을 밝힙니다. **근거: §4.1·14.**

### Q19. 학생이34배 작으면34배 빠른가요?
그렇지 않습니다. 커널 구현·메모리·전처리·batch·하드웨어가 실제 지연을 결정합니다. 동일 CPU에서 중앙값·p95와 처리량을 따로 측정합니다. **근거: §15.**

### Q20. 증류가 개선되지 않으면 실패인가요?
통제된 비교에서 이득이 없다는 결과도 유효합니다. M3나 M0로 충분한 조건을 찾으면 배포 선택과 불필요한 교사 비용을 줄이는 근거가 됩니다. 유리한 seed만 남기거나 계속 탐색해 원하는 결과를 만들지 않습니다. **근거: §1·17.**

### Q21. 실제 서비스나 다른 학교 네트워크에서도 되나요?
현재는 CESNET 자료와 지정 서비스·기간의 결과입니다. 다른 환경·클라이언트·수집 도구에서의 적용과 실시간 수집 품질은 별도 검증이 필요합니다. **근거: §4·15·18.**

### Q22. 원 논문을 똑같이 재현한 건가요?
공개 구조·가중치·선택한 전이 경로를 기반으로 목표2025년 서비스 과제에 적응시킨 비교입니다. 원천 사전학습 전체와 논문의 모든 데이터·분할·학습 설정을 그대로 반복한 것은 아닙니다. **근거: §9.1, 계획서 대응표.**

### Q23. 성능 목표를 달성했다고 언제 말할 수 있나요?
대표 조건5회 본실험을 평가한 결과,4월 M2 대비 M5 손실은 평균21.028%p이며 다섯 반복 모두2%p를 넘었습니다. 따라서 이번 성능 목표는 미달입니다. 파라미터는34.47배 작고 지정 CPU batch1 지연은약8.86배 짧지만 이것만으로 성능 보존 목표까지 달성했다고 말하지 않습니다. **근거: §1·14·15·대표 본실험 결과.**

### Q24. 아직 해결하지 못한 것은 무엇인가요?
개발60회와 별도로 본학습180회(대표30+후속150),4·5월360평가,CPU180모델 측정을 완료하고 원본을 검증했습니다. 본실험에서는 실행별 CUDA peak allocation과 CPU 프로세스 RSS/peak도 기록했습니다. 후속 라벨 예산·서비스 구성 비교와 CPU 재생 시연까지 진행했습니다. 남은 것은 학생의 격차 원인 분리, 실제 패킷 수집 시연과 새 환경 검증입니다. 세션 단위 누수·원천 사전학습 중복·새 환경 일반화는 현재 입증 범위 밖입니다. **근거: §17·18·20·대표 본실험 결과.**

## 20. 주장–근거–남은 일 대조표

이 표는 작성자가 합의문·코드를 직접 대조한 자체 검토다. 독립 검토자나 전 데이터 재검증을 수행했다고 표현하지 않는다.

| 주장/요구 | 판정 | 증거 | 남은 일·범위 |
|---|---|---|---|
| 첫≤30 PPI·짧은flow·고정변환 | implemented | config/data/models,실제shape snapshot | 실시간수집기의동일전처리검증별도 |
| 1월내정제·균등·중첩 | implemented | prepared manifest/curation/verify | 세션단위분리보장아님 |
| M1/M2구조동일·BN차이명시 | implemented | make_model/Teacher.train/param | 초기가중치단일요인결론불가 |
| M3/M4/M5강한통제 | implemented | init/data/RNG설계·smoke·회수각run의hash대조 통과 | 장비/버전 간 bitwise 동일성은 보장하지 않음 |
| 본실험학습길이동결 | implemented | main_frozen.json·실행기 범위/해시 검사·50epoch | 성능을 본 뒤 변경하지 않음 |
| 설정탐색의최종성능독립성 | partial | 별도devseed와2월선택 | 공통검증의선택적응과과거평가접근한계 |
| run별원본·복구·전체후보보존 | implemented(개발·대표본실험) | 개발60회·본학습30회 원본,별도 환경/로그,해시 검증 | 향후 실행도 원장 등록 필요 |
| 최종5회평균·부분집합·CPU비용 | 필수6조건 완료 | 본학습180·월별360·CPU180 및 검증원장 | 실제네트워크수집 지연·선택확장은 별도 |
| ‘모든정보기록·한계없음’ | 주장하지 않음 | §17의미기록항목·Q&A | 추가기록을완료여부별로관리 |

## 21. 발표 자료로 옮기는 순서

1. **문제와 질문:** 왜 저라벨 학습·경량 학생이 필요한지, 중간발표에서 검증할 질문은 무엇인지 설명한다.
2. **데이터와 통제:** 기간·서비스·표본 수·입력·정제·평가 정의를 한 슬라이드로 정리한다.
3. **모델 지도:** M0~M5의 구조 계열과 학습 신호, 교사·학생의 계층도를 보여준다.
4. **개발과 본 평가 분리:** 무엇을2월에서 선택하고 무엇을4·5월에서 비교하는지 구분한다.
5. **대표 결과:** 완료된 본 실험만 평균·표준편차·5개 반복의 짝 차이·CPU 비용 표로 제시한다.
6. **어디서 실패하는가:** Google 서비스 혼동·패킷 길이·학습 입력 겹침 여부로 나누어, 표본 수와 함께 설명한다.
7. **결론과 남은 일:** 결과가 허용하는 주장, 목표 달성 여부, 다음 검증을 정리한다.

부록에는 서비스별 support, 전체 후보 표, 학습곡선, 정확한 구조·설정·라벨 접근량·출처 해시·Q&A를 둔다. 발표 본문을 모든 로그로 채우지 않되, 질문을 받으면 원장과 원본 파일까지 내려갈 수 있게 연결한다.

## 22. 원본·출처·재생성 안내

- [원 계획서 추출본](snapshots/original_plan_text.txt), [사용자가 제공한 설정 설명 원문](snapshots/settings_explanation_user_supplied.txt).
- [선택 당시 결정 기록 snapshot](snapshots/restart_decisions_at_capture.md), [최신 결정 기록](../../experiments/2026-10-28_data_audit/restart_decisions.md).
- [실행 설정 snapshot](snapshots/config.json), [모델 구현](snapshots/models.py), [데이터 구현](snapshots/data.py), [학습 구현](snapshots/training.py), [개발 실행기](snapshots/colab_development.py).
- [공식 생성자 소스](snapshots/official_model_factory.py), [공식 backbone 소스](snapshots/official_multimodal_cesnet_enhanced.py), [pooling 소스](snapshots/official_pooling.py), [CESNET BSD-3-Clause 고지](snapshots/CESNET_LICENCE.txt).
- [구조와 shape·IPT bin snapshot](snapshots/architecture.json), [snapshot 출처·SHA256](snapshots/source_hashes.json).
- [준비 데이터 manifest](../../experiments/2026-10-30_midterm_restart/prepared/manifest.json), [CPU 연결 점검 — 원본 로컬 보관](../../PUBLICATION.md#omitted-artifacts), [해당 시점 검증 기록](../../experiments/2026-10-30_midterm_restart/verification.json).
- [현재 실행 README](../../experiments/2026-10-30_midterm_restart/README.md), [Colab 노트북](about:blank#private-workspace-link-omitted).

본 문서는 로컬 코드·원본 기록을 근거로 작성했다. 논문 출처와 공식 모델 링크는 기존 계획서·보존 소스의 출처이며, 이 문서 작성으로 모든 외부 논문의 최신내용을 새로 검증했다고 주장하지 않는다. 원자료·공개 모델의 배포 조건과 제공자 고지는 재배포 시 함께 유지한다. 개인정보·계정정보가 보이는 브라우저 전체 화면을 팀 공유 자료에 그대로 싣지 않는다.
