# 팀원용 재현 안내: 데이터와 가중치 준비부터 실행까지

대상은 **2026-10-30~31 중간발표 실험**입니다. 11월 후속 실험은 이 저장소에 없습니다.

추천 순서는 **공식 파일 2개 받기 → 데이터 다시 준비 → 작은 동작 점검 → 대표 조건 30회 → 결과 검증**입니다. 라벨 수·서비스 구성 비교까지 필요할 때 나머지 150회를 실행합니다. 아래 명령은 저장소 루트에서 실행합니다.

## 먼저 고르기

| 목적 | 필요한 것 | 학습 여부 |
|---|---|---|
| 기존 보고서·그림·CSV 보기 | 저장소만 | 없음 |
| 같은 설계로 다시 학습 | 저장소 + 아래 공식 데이터·사전학습 가중치 + CUDA GPU | 새 학습 |
| 당시 모델로 추론만 다시 하기 | 당시 `best.pt`/M0 `best.txt`, 대응 설정·클래스 목록·검증 원장 + 평가 데이터 | 재학습 불필요 |

**당시 학습한 최종 가중치와 예측 배열은 GitHub에 없습니다.** 추론만 하려면 프로젝트 담당자가 로컬 보관 중인 해당 실행의 검증된 원본 ZIP을 따로 전달해야 합니다. 아래에서 받는 공개 `.pth`는 CESNET의 **초기 사전학습 가중치**이며, 우리 20서비스에 미세조정한 최종 모델이 아닙니다. M1과 M3는 무작위 초기화, M2는 공개 가중치에서 시작하고, M4/M5는 이번 실행에서 학습한 M1/M2를 각각 사용합니다.

보고서만 볼 때:

```sh
git clone https://github.com/RealOctavision/helloworld.git
cd helloworld
python3 -m http.server 8000 --bind 127.0.0.1
# 브라우저: http://127.0.0.1:8000/reports/2026-10-31_midterm_report/report.html
```

## 1. 새 실행 폴더와 Python 환경

재학습은 기존 결과 열람용 폴더와 **별도의 새 clone**에서 진행합니다. 아래 준비 블록은 처음 한 번만 실행합니다. 재개할 때 다시 초기화하지 않습니다.

```sh
git clone https://github.com/RealOctavision/helloworld.git helloworld-reproduce
cd helloworld-reproduce
git rev-parse HEAD > reproduction_commit.txt
python3 -m venv .venv
source .venv/bin/activate
export EXP=experiments/2026-10-30_midterm_restart
```

- 본학습 실행기는 **NVIDIA CUDA**가 있어야 실행됩니다. Linux/WSL2 또는 Colab의 Linux 터미널을 기준으로 설명합니다. Windows 네이티브에서는 `fcntl` 때문에 그대로 실행되지 않습니다. Mac은 자료 열람·데이터 준비·CPU 점검에 사용할 수 있지만 이 본학습 실행기는 MPS를 지원하지 않습니다.
- 기존 GPU 기록은 **A100-SXM4-40GB / Python 3.13.16 / Torch 2.11.0+cu130 / NumPy 2.1.3 / cesnet-models 0.4.1 / LightGBM 4.6.0**입니다. Python 3.13 환경으로 맞추는 것이 비교에 유리합니다.
- 아래 설치 예시는 CUDA 13.0을 지원하는 드라이버가 있는 Linux용입니다. 다른 환경은 [PyTorch 공식 버전별 설치 안내](https://pytorch.org/get-started/previous-versions/)에서 맞는 wheel을 선택하고 달라진 환경을 기록하세요.

```sh
python -m pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cu130
python -m pip install numpy==2.1.3 cesnet-models==0.4.1 lightgbm==4.6.0 tables==3.11.1
python -m pip check
python -m pip freeze > reproduction_environment.txt
```

`requirements.txt`는 **당시 Mac 점검 환경**의 기록입니다. GPU 환경에 그대로 적용하는 설치 파일로 보지 마세요. 원래 HDF5 감사는 Python 3.12.14·NumPy 2.3.5·PyTables 3.11.1에서 수행했고, 준비·학습 환경이 서로 달랐습니다. 아래 데이터 대조로 동일한 입력인지 확인합니다.

여유 디스크는 캐시·체크포인트·원본 ZIP·검증용 사본을 고려해 **30GB 이상을 계획값으로** 잡으세요. 이는 측정한 최소 요구량은 아닙니다. 데이터 준비는 GPU가 필요 없으므로 가능하면 GPU 이용 시간 전에 끝냅니다. CPU에서 준비해 GPU 장비로 옮길 때도 저장소의 상대경로 구조를 유지해야 합니다.

## 2. 공식 파일 두 개 다운로드·확인

| 파일 | 기록된 크기 | 저장 위치 |
|---|---:|---|
| `CESNET-QUICEXT-25-XS.h5` | 3,544,625,537 bytes (약 3.54GB) | `research/2026-09-22_plan_support/data/` |
| `30pktTCNET_256_CESNET_QUIC22_Week46_Domains.pth` | 7,179,018 bytes (약 7.18MB) | `research/2026-09-22_plan_support/models/` |

XS 파일 하나를 사용합니다. Zenodo의 월별 원본 ZIP 전체를 받을 필요는 없습니다. [데이터 출처](https://zenodo.org/records/17249078), [교사 코드·가중치 출처](https://github.com/CESNET/cesnet-models), [배포 조건과 기록된 해시](PUBLICATION.md)를 참고하세요.

```sh
curl -fL --retry 3 -C - \
  'https://liberouter.org/datazoo/download?bucket=cesnet-quicext-25&file=CESNET-QUICEXT-25-XS.h5' \
  -o research/2026-09-22_plan_support/data/CESNET-QUICEXT-25-XS.h5
curl -fL --retry 3 -C - \
  'https://liberouter.org/datazoo/download?bucket=cesnet-models&file=30pktTCNET_256_CESNET_QUIC22_Week46_Domains.pth' \
  -o research/2026-09-22_plan_support/models/30pktTCNET_256_CESNET_QUIC22_Week46_Domains.pth

python - <<'PY'
import hashlib
from pathlib import Path
checks = [
    ('data/CESNET-QUICEXT-25-XS.h5', 3544625537,
     '6b323c4c53b7c9d0ec9011f895b3c5ba6b35247576e41ef19fe84ab8632810ab'),
    ('models/30pktTCNET_256_CESNET_QUIC22_Week46_Domains.pth', 7179018,
     'dc4b3333388239ac25b8c028c922965e2333cc151dd5fad951950099e86fabc4'),
]
for name, size, expected in checks:
    p = Path('research/2026-09-22_plan_support') / name
    assert p.stat().st_size == size, f'크기 불일치: {p}'
    with p.open('rb') as f:
        assert hashlib.file_digest(f, 'sha256').hexdigest() == expected, f'SHA 불일치: {p}'
    print('OK', p.name)
PY
```

다운로드가 실패하거나 해시가 다르면 그 상태로 학습하지 않습니다. 새 모델이나 비슷한 이름의 데이터로 대신하면 기존 실험의 재현이 아닙니다.

## 3. 과거 결과 보관 후 데이터 재생성

저장소에는 `manifest.json` 같은 **완료 기록**은 있지만 실제 NPY/NPZ는 없습니다. 기록을 그대로 두면 준비 코드가 건너뛰거나 파일 없음 오류를 냅니다. 다음 코드는 새 clone 안에서 과거 기록을 `tmp/published_baseline/`로 옮겨 보관합니다. 모델·학습 코드와 고정 설정은 바꾸지 않습니다.

```sh
python - <<'PY'
from pathlib import Path
import shutil, json, hashlib
root = Path.cwd()
e = root / 'experiments/2026-10-30_midterm_restart'
backup = root / 'tmp/published_baseline'
assert not backup.exists(), '초기화는 한 번만! 기존 실행을 보존하세요.'
assert not any((e / x).exists() for x in ['main_training', 'main_evaluation', 'continuation']), '이미 시작한 실행입니다.'
paths = [
    Path('experiments/2026-10-28_data_audit/manifest.json'),
    *[e.relative_to(root) / name for name in
      ['prepared', 'main_recovered', 'continuation_recovered', 'main_cpu_benchmark']],
]
for rel in paths:
    src, dst = root / rel, backup / rel
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
# 새 실행 시작 전의 코드 지문. 과거 전송 기록을 새 결과의 근거로 재사용하지 않습니다.
names = ['config.json', 'main_frozen.json', 'data.py', 'models.py', 'training.py', 'colab_main.py']
def fingerprint(names):
    return {str((e / n).relative_to(root)): hashlib.sha256((e / n).read_bytes()).hexdigest() for n in names}
for filename, value in [
    ('main_transfer_metadata.json', {'files': fingerprint(names)}),
    ('continuation_split_transfer.json', {'train': {'files': fingerprint(names + ['continuation_frozen.json', 'colab_continuation.py'])}}),
]:
    p = e / filename
    assert not p.exists(), f'기존 전송 기록 보존 필요: {p}'
    p.write_text(json.dumps(value, indent=2) + '\n')
print('과거 기록 보관 및 새 실행 코드 지문 저장 완료')
PY

python experiments/2026-10-28_data_audit/analyze.py --prepare-only
python "$EXP/data.py" self-test
python "$EXP/data.py" prepare
```

이 과정에서 `ppi.npy`, `meta.npy`, `prepared/`의 39개 NPZ가 생성됩니다. **2025년 1월 학습 → 2월 검증 → 4월·5월 평가**, 클래스 목록·seed·정제 규칙은 코드가 고정합니다. 직접 랜덤 분할하거나 3월 데이터를 추가하지 마세요. `config.json`, `main_frozen.json`, `continuation_frozen.json`은 해시로 연결되어 있으므로 재현 중 수정하지 않습니다.

다음 대조는 GPU 학습 전에 수행합니다. 과거 준비 기록과 모든 NPZ의 SHA-256을 비교합니다. 환경에 따른 저장 형식 차이도 실패로 나올 수 있으므로 실패 시 데이터·배열 내용을 확인해야 하며, 기대 해시를 임의로 바꾸지 않습니다.

```sh
python - <<'PY'
import json, hashlib
from pathlib import Path
e = Path('experiments/2026-10-30_midterm_restart')
old = json.loads((Path('tmp/published_baseline') / e / 'prepared/manifest.json').read_text())
new = json.loads((e / 'prepared/manifest.json').read_text())
assert old['config_sha256'] == new['config_sha256']
assert old['source_sha256'] == new['source_sha256']
assert old['cache_sha256'] == new['cache_sha256'], '원본 PPI 캐시 불일치'
assert old['cohorts'] == new['cohorts'], '분할/정제 집계 불일치'
for rel, expected in old['artifacts'].items():
    if rel.endswith('.npz'):
        with (e / 'prepared' / rel).open('rb') as f:
            actual = hashlib.file_digest(f, 'sha256').hexdigest()
        assert actual == expected, f'준비 배열 불일치: {rel}'
print('원본과 동일한 캐시·분할·39개 NPZ 확인')
PY
```

## 4. 작은 점검 → 대표 조건 본실험

```sh
python "$EXP/smoke.py" --output smoke_team
```

이것은 CPU에서 작은 2epoch 학습·복구 등을 검사하는 **동작 점검**입니다. `smoke_team/summary.json`의 `status: passed`를 확인합니다. 이 점수를 본실험 성능으로 쓰지 않습니다. 기존 `verify.py`는 당시의 `smoke_v2`와 비공개 `cache_source_check.json`도 요구하므로 새 clone의 준비 확인 명령으로 바로 실행하지 않습니다.

CUDA 확인 후 본실험:

```sh
python - <<'PY'
import torch
assert torch.cuda.is_available(), 'CUDA GPU를 먼저 준비하세요.'
print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))
PY
python "$EXP/colab_main.py" --minutes 45
```

이 명령은 **Google 포함 20서비스 × 서비스당 200개 × M0~M5 × seed 201~205 = 30회**를 실행하고, 완료 모델을 고정한 뒤 4·5월 **60건 평가**를 합니다. M0는 CPU LightGBM이며 신경망은 CUDA입니다. 학생·교사를 직접 하나씩 실행하거나 KD 교사를 수동 교체할 필요가 없습니다.

- `main_status.json`의 상태와 완료 수를 봅니다. `completed`가 최종 완료이고 `budget_stopped`는 일부 완료입니다.
- `--minutes 45`는 **한 번 호출의 실행 예산**이며 완료 예상 시간이나 GPU 자동 해제 기능이 아닙니다. 체크포인트/압축 시간까지 포함한 클라우드 청구 상한을 보장하지도 않습니다.
- 시간 제한으로 멈췄다면 파일을 보존한 같은 환경에서 같은 명령을 다시 실행하면 완료 fit을 확인하고 중단 fit을 재개합니다. 먼저 기존 프로세스가 끝났는지 확인하고, 남은 GPU 예산 안에서만 재개합니다.
- 런타임 자체가 삭제되면 `/content`의 파일도 사라집니다. 이 경우 같은 명령만으로 자동 복구되지 않으므로 별도 보관한 실행 폴더/체크포인트가 필요합니다.
- `failed`/NaN/해시 오류는 원인 확인 대상입니다. 자동으로 초기화하거나 설정을 바꾸고 같은 실험이라고 기록하지 않습니다.

## 5. 결과 원본 보관·검증

대표 조건의 산출물은 아래 두 쌍입니다. 원격 GPU에서 실행했다면 **ZIP과 `.zip.json` 모두 로컬로 복사**하고 아래 명령을 로컬 저장소 루트에서 실행합니다. 로컬에도 동일한 준비 데이터와 시작 전에 만든 `main_transfer_metadata.json`이 있어야 합니다.

- `$EXP/main_training_results.zip` + `main_training_results.zip.json`
- `$EXP/main_evaluation_results.zip` + `main_evaluation_results.zip.json`

```sh
python - <<'PY'
import json, subprocess, sys
from pathlib import Path
e = Path('experiments/2026-10-30_midterm_restart')
for kind in ['training', 'evaluation']:
    archive = e / f'main_{kind}_results.zip'
    meta = json.loads(archive.with_suffix('.zip.json').read_text())
    subprocess.run([sys.executable, str(e / 'verify_main_results.py'), kind,
                    '--archive', str(archive.resolve()), '--sha256', meta['sha256']], check=True)
PY
```

검증기는 ZIP 전체 SHA·CRC·안전 경로·내부 파일 해시·실행 설정·체크포인트·평가 ID 및 지표를 대조하고 `main_recovered/`에 원본과 검증 원장을 저장합니다. **학습 30회와 평가 60건의 검증 성공 및 로컬 파일 보존을 확인한 후 GPU를 해제**합니다. 새 학습의 체크포인트 SHA가 과거 가중치 SHA와 다르다는 이유만으로 손상은 아닙니다. 새 실행 내부의 지문·설정·입력 연결과 지표를 검증해야 합니다.

GPU를 해제한 뒤 CPU 비용을 측정하려면:

```sh
python - <<'PY'
import json, subprocess, sys
from pathlib import Path
e = Path('experiments/2026-10-30_midterm_restart')
reg = json.loads((e / 'main_recovered/training_registry.json').read_text())
v = json.loads(Path(reg['verification']).read_text())
subprocess.run([sys.executable, str(e / 'main_cpu_benchmark.py'),
                '--root', v['extracted'], '--output', str(e / 'main_cpu_benchmark')], check=True)
PY
python reports/2026-10-30_midterm_research_record/build_continuation_summary.py
```

통합 요약기는 대표 조건만 완료되어도 새 결과를 표시하고 나머지 조건은 미완료로 둡니다. 새 표는 `reports/2026-10-30_midterm_research_record/continuation_results.md`, 기계 판독 수치는 `$EXP/continuation_recovered/continuation_summary.json`입니다. CPU 측정 중 다른 무거운 작업은 함께 실행하지 않습니다. 장비가 달라지면 당시 CPU 지연 수치와 직접 같은 값이 나오지 않습니다.

## 6. 선택: 나머지 150회까지 재현

대표 조건까지 확인한 뒤 전체 중간발표 범위를 재현할 때 실행합니다. 대표 200개 조건은 다시 학습하지 않습니다.

```sh
python "$EXP/colab_continuation.py" --minutes 110
```

| stage | 학습 조건 | fit 수 |
|---|---|---:|
| `mixed_n50` | Google 포함20, 서비스당 50개 | 30 |
| `mixed_n100` | Google 포함20, 서비스당 100개 | 30 |
| `mixed_n1000` | Google 포함20, 서비스당 1,000개 | 30 |
| `nongoogle_n200` | 비Google13, 서비스당 200개 | 30 |
| `googleonly_n200` | Google 계열20, 서비스당 200개 | 30 |

`110` 역시 한 번 호출의 예산입니다. GPU를 유지해 연속 실행하는 경우나 나중에 새 GPU에서 실행하는 경우 모두 해당 장비의 이용 예산을 별도로 관리하세요. 완료 상태는 `$EXP/continuation/status.json`에서 확인합니다.

각 stage마다 `$EXP/continuation_archives/`에 `{stage}_training.zip`과 `{stage}_evaluation.zip`, 각 `.zip.json`이 생성됩니다. 5개 stage의 **10개 ZIP + 메타데이터**를 로컬에 보관하고 검증합니다. 원격 평가는 신경망 250건이며, M0 50건은 회수 검증 후 CPU에서 평가합니다.

```sh
python - <<'PY'
import json, subprocess, sys
from pathlib import Path
e = Path('experiments/2026-10-30_midterm_restart')
plan = json.loads((e / 'continuation_frozen.json').read_text())
for stage in plan['stages']:
    sid = stage['id']
    for kind in ['training', 'evaluation']:
        a = e / 'continuation_archives' / f'{sid}_{kind}.zip'
        m = json.loads(a.with_suffix('.zip.json').read_text())
        subprocess.run([sys.executable, str(e / 'verify_continuation_results.py'), kind,
                        '--stage', sid, '--archive', str(a.resolve()), '--sha256', m['sha256']], check=True)
PY
```

로컬 보존·모든 검증이 끝났으면 GPU를 해제합니다. 이후 CPU에서 순서대로 실행합니다.

```sh
for stage in mixed_n50 mixed_n100 mixed_n1000 nongoogle_n200 googleonly_n200; do
  python "$EXP/local_m0_evaluation.py" --stage "$stage" || break
  python "$EXP/continuation_cpu_benchmark.py" --stage "$stage" || break
done
python reports/2026-10-30_midterm_research_record/build_continuation_summary.py
```

본학습 **180회**, 월별 평가 **360건**, CPU 측정 **180개**가 모두 완료되면 새 `continuation_summary.json`의 `complete`가 `true`가 됩니다. 개발 60회는 선택된 고정 설정을 재사용했으므로 새로 실행한 수에 더하지 않습니다. 하이퍼파라미터 탐색 과정까지 다시 하려면 `colab_development.py`가 별도 대상이며, 그 결과로 설정을 변경하면 이 고정 설정 재현과 구분해 기록해야 합니다.

## 7. 무엇을 비교하면 되나요?

대표 조건 4월 자연분포 `all`의 기존 참고값은 다음과 같습니다. 각 값은 5seed 평균 ± 표본 표준편차입니다.

| 모델 | 기존 Macro-F1 |
|---|---:|
| M2: 사전학습 교사 | 53.771 ± 1.743% |
| M3: 일반 학생 | 32.493 ± 0.982% |
| M5: M2에서 KD한 학생 | 32.743 ± 0.815% |

새 실행에서도 **같은 월·조건·그룹·5seed**로 M5−M3(KD 추가 효과), M2−M5(교사 격차)를 비교합니다. 특정 seed 하나나 2월 검증점수를 위 표와 바로 비교하지 않습니다. 같은 설정이어도 GPU·CUDA·패키지가 달라지면 가중치와 점수의 완전한 일치는 보장하지 않습니다.

`reports/2026-10-31_midterm_report/`의 완성 보고서와 발표 그림은 **당시 결과**입니다. 보고서 생성기의 `content.md`에도 당시 해석이 들어 있으므로 실행만 하면 새 실험 보고서가 완성되는 것은 아닙니다. 새 검증 원장·통합 수치로 새 글을 작성하고 환경·완료 범위·차이를 기록하세요. 과거 개발 결과나 CPU 측정이 새로 수행된 것처럼 섞이지 않게 합니다.

## 자주 막히는 지점

| 증상 | 확인할 것 |
|---|---|
| `ppi.npy`/NPZ 없음, 이미 준비됐다는 메시지 | 3절의 최초 기록 보관 단계를 했는지 |
| `Frozen protocol` / `Core source changed` | 원본 고정 파일 수정, 줄바꿈 변환, 잘못된 버전을 섞었는지; 해시 검사를 끄지 않기 |
| 공개 교사 파일 SHA 불일치 | `.pth` 파일명·크기·다운로드 완료 여부 |
| `CUDA` 없음 | 드라이버·CUDA용 Torch·GPU 런타임; CPU/MPS로 본학습 강행하지 않기 |
| `main_transfer_metadata.json` 없음 | 3절의 새 실행 코드 지문 저장; 과거 비공개 전송 파일을 대신 넣지 않기 |
| `run.sh`에서 Python 경로 오류 | 활성화한 `.venv`의 `python script.py` 사용 |
| 한글 폰트/그림 생성 오류 | 발표 그림 생성기는 Mac 폰트 경로를 사용; 다른 OS는 폰트 설정 필요 |

이 안내는 공개 코드의 실제 CLI·파일 참조·고정 해시·소형 점검을 확인해 작성했습니다. **이 문서 작성 중 새 Linux/Colab 환경 설치, 전체 데이터 재생성, GPU 본학습을 다시 수행한 것은 아닙니다.** 공식 파일의 로컬 검증과 단계별 완료 확인을 거쳐 재현 여부를 판단하세요.
