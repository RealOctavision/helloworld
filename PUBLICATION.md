# 공개 사본의 범위와 재현 조건

이 저장소는 캡스톤 실험의 **공개용 기록 사본**입니다. 중간발표 기록에 2026-11-05 M3 채널 확대 학습과 11-08 최종 평가를 별도 추가했습니다. 각 원본 실험 기록은 보존하고 공개용 집계·재현 안내를 제공합니다.

## 포함한 자료

- 11월 M3 채널 확대의 학습·평가 코드, 출력 없는 Colab 템플릿, 학습 4회·최종 평가 8회의 집계 수치와 검증·환경 기록. [후속 보고서](reports/2026-11-08_m3_width_final/README.md)를 참고하세요.

- 10/30~31 M0–M5 실험의 데이터 처리·학습·증류·평가·CPU 측정·복구 검증 코드와 고정 설정.
- 등록된 개발 60회, 본학습 180회와 월별 평가의 집계 지표·학습 이력·검증 원장, CPU 측정 결과.
- 연구 원장, 최종 보고서(HTML/Markdown/Word), 발표용 그림 27종(PNG/SVG), 그래프의 CSV와 생성 코드.
- 그 실험에 필요한 사전 데이터 감사 집계와 공식 데이터·모델의 출처·해시.
- `experiments/2026-10-05_service20_label_ablation/protocol.json`은 사전 감사가 참조하는 기존 클래스 목록의 의존성으로만 포함했습니다. 해당 날짜의 실험 결과 전체를 추가한 것은 아닙니다.

<a id="omitted-artifacts"></a>
## 공개 사본에서 제외한 자료

원시 HDF5/NPY/NPZ, 실제 PPI·source ID가 들어 있는 예시, 개별 예측 배열, 모든 학습 체크포인트/PT/PTH/BIN, 업로드·회수 ZIP과 전송 조각, 가상환경, 캐시, 임시 검토 이미지, 계정·런타임 화면, 개인 Colab 문서 링크를 제외했습니다. 중간발표 원본은 로컬에, 11월 학습·평가 원본 ZIP은 프로젝트 Drive에 보관되어 있습니다. 11월 ZIP의 SHA-256·CRC는 Colab과 Drive 사본에서 확인했으며 로컬 ZIP 다운로드를 완료했다고 주장하지 않습니다.

보고서에서 제외된 파일로 연결되는 링크는 **“원본 로컬 보관”** 표시 또는 링크 설명과 함께 이 절로 연결했습니다. 문서 안의 경로 문자열은 원장 추적을 위해 남아 있을 수 있지만 해당 원자료가 GitHub에 있다는 뜻은 아닙니다. Word 파일은 원본 보고서 형식을 유지하므로 일부 로컬 근거 경로가 남을 수 있습니다.

## 원본 무결성과 공개 파일 해시

11월 추가·수정 파일은 [후속 공개 파일 원장](reports/2026-11-08_m3_width_final/publication_manifest.json)으로 확인합니다. 이 원장은 루트 안내 문서 변경도 포함하며 자기 자신의 해시는 포함하지 않습니다. 아래 기존 원장은 중간발표 공개 당시 범위를 유지합니다.

[publication_manifest.json](publication_manifest.json)은 파일별 원본 상대경로·크기·SHA-256과 공개 파일 크기·SHA-256을 구분합니다. 일부 큰 JSON은 공백만 압축했고 개인 작업 경로·문서 주소를 지웠습니다. Markdown/HTML의 미포함 자료 링크도 명시적으로 바꿨습니다. 모든 변환 종류를 파일별로 기록했습니다.

기존 `verified_*.json`, manifest 및 보고서에 있는 archive/file hash는 **당시 검증한 로컬 원본의 해시**입니다. 공개 파일에 맞춰 원본 해시를 다시 쓰지 않았습니다. 수정된 공개 사본의 무결성은 `publication_manifest.json`의 `published_sha256`으로 확인해야 합니다. 원본 ZIP·체크포인트를 배포하지 않으므로 기존 원본 회수 검증기를 이 저장소만으로 통과시킬 수 있다고 주장하지 않습니다.

## 실행 환경과 다시 실행할 수 있는 범위

완성 보고서·그림·CSV 열람은 Python HTTP 서버만으로 가능합니다. 그림 생성 코드는 기존 Mac의 한글 폰트 경로를 사용합니다. 다른 OS에서는 폰트를 준비하고 경로를 조정해야 하며, 이번 업로드에서 다른 OS 재생성까지 검증하지 않았습니다.

학습 코드는 당시 실행 구현을 보존했습니다. 로컬 점검의 버전은 [requirements.txt](experiments/2026-10-30_midterm_restart/requirements.txt)에 있고, A100의 Torch/CUDA 환경은 검증 원장에 별도 기록되어 있습니다. `run.sh`는 원래 프로젝트의 가상환경 경로를 사용합니다. 새 환경에서는 Python 3.12 이상과 해당 장비에 맞는 Torch, NumPy, cesnet-models 0.4.1, LightGBM 및 데이터 감사용 PyTables를 준비해야 합니다. 설치와 새 학습은 자동으로 실행되지 않습니다.

전체 학습·CPU 시연·보고서 원본 해시 대조에는 추가로 아래 데이터·가중치와 원래 준비/결과 산출물이 필요합니다. 기존 고정 설정 및 데이터 ID·파일 해시를 유지해야 하며, 일부 자료가 없는 상태에서 원본과 동일한 실험을 재현했다고 표시하면 안 됩니다.

## 공식 데이터와 교사 가중치 출처

데이터는 [CESNET-QUICEXT-25](https://zenodo.org/records/17249078), 데이터 처리 소프트웨어는 [CESNET DataZoo](https://github.com/CESNET/cesnet-datazoo)입니다. XS 배포 및 원본 ZIP의 조건을 구분한 기록은 [데이터 manifest](research/2026-09-22_plan_support/data/manifest.json)에 있습니다. 본 저장소는 원시 데이터나 XS 파일을 재배포하지 않습니다.

- 공식 XS 파일명: `CESNET-QUICEXT-25-XS.h5`
- 공식 다운로드: <https://liberouter.org/datazoo/download?bucket=cesnet-quicext-25&file=CESNET-QUICEXT-25-XS.h5>
- 기록된 크기: 3,544,625,537 bytes
- SHA-256: `6b323c4c53b7c9d0ec9011f895b3c5ba6b35247576e41ef19fe84ab8632810ab`
- 원래 상대경로: `research/2026-09-22_plan_support/data/CESNET-QUICEXT-25-XS.h5`

교사 코드·가중치 출처는 [CESNET Models](https://github.com/CESNET/cesnet-models)이며, [모델 manifest](research/2026-09-22_plan_support/models/manifest.json)에 패키지·출처 commit·사전학습 정보가 있습니다.

- 공식 가중치: `30pktTCNET_256_CESNET_QUIC22_Week46_Domains.pth`
- 공식 다운로드: <https://liberouter.org/datazoo/download?bucket=cesnet-models&file=30pktTCNET_256_CESNET_QUIC22_Week46_Domains.pth>
- 기록된 크기: 7,179,018 bytes
- SHA-256: `dc4b3333388239ac25b8c028c922965e2333cc151dd5fad951950099e86fabc4`
- 원래 상대경로: `research/2026-09-22_plan_support/models/30pktTCNET_256_CESNET_QUIC22_Week46_Domains.pth`

공식 코드 snapshot에는 원본의 [BSD-3-Clause 라이선스](reports/2026-10-30_midterm_research_record/snapshots/CESNET_LICENCE.txt)를 함께 보존했습니다. 별도 가중치 재배포 조건은 독립적으로 확인되지 않아 공식 URL·해시만 제공합니다. 이 업로드로 제3자 자료의 권리를 변경하거나 프로젝트 전체에 새로운 오픈소스 라이선스를 부여하지 않습니다.
