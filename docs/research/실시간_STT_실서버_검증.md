# 실시간 STT 실서버 검증 (2026-10-13)

[실시간 STT 파이프라인 평가](실시간_STT_파이프라인_평가.md)의 추천 중 확정 쪽(Silero 분할, 작업 스레드 2개)과 LLM 블로킹 수정을 main에 넣은 뒤, 실제 서버 WebSocket 경로로 다시 잰 결과다.

## 1. 요약

| 항목 | 수정 전 main | 현재 main |
|---|---|---|
| 확정 자막 정확도 (100초 스트림) | 71~78% (CER 0.223~0.290) | **평균 91.5%** (CER 0.049~0.111) |
| 확정 자막 정확도 (30분 연속) | 측정 안 함 | **92.1%** (CER 0.079) |
| 늦은 확정 (3,500ms 초과로 강등) | LLM 응답이 느리면 발생 | **0개** (30분, 확정 256개) |
| 확정 작업 대기 시간 | LLM 호출 시 최대 20,000ms | **최대 0ms** |
| 서버 메모리 (30분) | 측정 안 함 | 1,026MB → 1,051MB, 10분 이후 고정 |
| GPU 메모리 (30분) | 측정 안 함 | 3,142MB, 변화 없음 |

정확도는 `100% − CER`이다. 글자 100개 중 몇 개를 맞혔는지로 읽는다.

## 2. 검증 대상

| 대상 | 내용 |
|---|---|
| 코드 | main `06d64ac` (PR #10, #11, #12 머지 후) |
| 회색 자막 | sherpa-onnx 한국어 streaming zipformer (변경 없음) |
| 확정 자막 | faster-whisper large-v3-turbo, `int8_float16`, CUDA |
| 확정 구간 분할 | Silero VAD v6 (`system_audio` 프로필: 무음 300ms, 조기 EOU 210ms, 최대 구간 12초) |
| 작업 스레드 | `LIVE_STREAM_WORKER_COUNT=2` (서버 실행 환경 변수로 지정. `.env`는 1 그대로) |
| 라이브 분석 | rule_based 전용 (PR #12) |
| 인증 | `AUTH_ENABLED=false` (시험용, 환경 변수로 지정) |

비교 기준인 "수정 전 main"은 PR #11·#12 이전 main(`0e1fc7f`, 에너지 VAD 무음 420ms·최대 1.8초, 작업 스레드 1개)이다.

## 3. 환경

| 항목 | 값 |
|---|---|
| GPU | NVIDIA GeForce RTX 5070 Laptop GPU (8GB), 드라이버 610.62 |
| CPU | AMD Ryzen AI 9 365 |
| 메모리 | 31GB |
| OS | Windows 11 Home |
| 서버 | 프로젝트 venv, `uvicorn server.app.main:app --host 127.0.0.1 --port 8011` |
| DB·큐 | Docker `caps-postgresql-dev`, `caps-redis-dev` |

## 4. 테스트 데이터

### 4.1 원본: FLEURS 한국어 40문장

- 출처: Hugging Face `google/fleurs`, `data/ko_kr/test.tsv`와 `data/ko_kr/audio/test.tar.gz` (테스트 세트, CC-BY-4.0)
- 사람이 위키 문장을 읽은 낭독 음성이다. 회의 대화는 아니다.
- 테스트 세트 전체 행에서 `random.Random(20260626).sample(rows, 40)`으로 40개를 뽑아 `fleurs_00`~`fleurs_39`로 이름 붙였다 (`prep_fleurs.py`).
- 정답 텍스트는 TSV의 원문 열(3번째 열)을 그대로 쓴다.

실제 회의 녹음은 대외비라 쓰지 않았다.

### 4.2 스트림 6개 (회의처럼 이어 붙인 음성)

`build_streams.py`가 만든다.

- 시드 `random.Random(20260627)` 하나로 스트림마다 순서대로 다음을 뽑는다.
  1. 40개 중 8개를 중복 없이 뽑는다 (`rng.sample`). 스트림끼리는 같은 클립이 다시 나올 수 있다.
  2. 클립 사이 무음 7개를 0.4~1.2초 균등분포로 뽑는다.
- 클립마다 피크를 0.9로 맞춘다.
- 클립 사이에는 디지털 무음(0)을 넣는다. 잡음은 섞지 않았다.
- 16kHz 모노 float32 WAV로 저장한다.
- 정답은 8개 클립 정답을 공백으로 이어 붙인 것이다.

| 스트림 | 길이(초) | 사용 클립 (`fleurs_XX`, 재생 순서) | 클립 사이 무음(초) | 정답 글자 수 |
|---|---|---|---|---|
| stream_00 | 99.0 | 37, 31, 02, 06, 15, 38, 24, 12 | 0.42~1.03 | 336 |
| stream_01 | 99.3 | 16, 15, 12, 39, 09, 03, 02, 23 | 0.40~1.06 | 379 |
| stream_02 | 93.8 | 24, 31, 34, 06, 16, 29, 01, 17 | 0.40~1.12 | 319 |
| stream_03 | 106.3 | 24, 30, 10, 22, 15, 19, 39, 09 | 0.67~1.14 | 357 |
| stream_04 | 100.8 | 30, 20, 36, 12, 19, 29, 14, 00 | 0.46~1.03 | 349 |
| stream_05 | 111.6 | 19, 00, 26, 05, 16, 38, 15, 36 | 0.47~1.18 | 384 |
| 합계 | 610.8 (약 10.2분) | 48자리, 서로 다른 클립 27개 | | 2,124 |

글자 수는 4.4의 정규화를 한 뒤 센 값이다.

### 4.3 30분 연속 음성

`long_session_eval.py`가 실행할 때 메모리에서 만든다.

- stream_00 → stream_05 순서를 3번 반복해 이어 붙인다 (18개).
- 스트림 사이에는 1초 무음을 넣는다.
- 길이는 30.8분, 정답은 18개 스트림 정답을 공백으로 이어 붙인 것이다.
- 같은 음성을 3번 반복하므로, 정확도는 새 음성 30분이 아니라 **장시간 운영에서 정확도가 떨어지지 않는지**를 보는 값이다.

### 4.4 정확도 채점 (CER)

`bench.py`의 `normalize()`와 `cer()`를 쓴다.

1. 정답과 인식 결과에서 한글 음절(`가`~`힣`), 영문, 숫자 이외의 문자를 모두 지운다. 공백과 문장부호도 지운다.
2. 소문자로 바꾼다.
3. 글자 단위 편집 거리(삽입·삭제·치환 각 1)를 정답 글자 수로 나눈다.

인식 결과는 세션 동안 받은 `archive_final`과 `late_archive_final` 텍스트를 받은 순서대로 공백으로 이어 붙인 것이다. 회색 자막(`preview`, `live_final`)은 채점하지 않는다.

## 5. 측정 절차

### 5.1 서버 기동

```powershell
cd D:\meeting-overlay-assistant
$env:AUTH_ENABLED="false"; $env:LIVE_STREAM_WORKER_COUNT="2"; $env:PYTHONIOENCODING="utf-8"
.\venv\Scripts\python.exe -m uvicorn server.app.main:app --host 127.0.0.1 --port 8011
```

`/health`가 `{"status":"ok"}`를 돌려준 뒤 시작한다. 서버는 기동 때 STT 모델을 미리 올린다(`stt_preload_enabled`).

### 5.2 재생 방식 (`e2e_ws_eval.py`, `long_session_eval.py` 공통)

오버레이 클라이언트가 하는 일을 스크립트로 흉내 낸다.

1. `POST /api/v1/sessions/` (`source_type: "system_audio"`)로 세션을 만들고 `POST /api/v1/sessions/{id}/start`로 시작한다.
2. `ws://127.0.0.1:8011/api/v1/ws/audio/{id}?input_source=system_audio`에 연결한다.
3. WAV를 16kHz 모노 PCM16(little-endian)으로 바꿔 100ms(3,200바이트)씩 보낸다. i번째 청크는 시작 시각 + (i+1)×100ms에 보내 실시간 속도를 지킨다.
4. 다 보낸 뒤 1초 무음을 더 보내고, 마지막 확정을 기다린다 (100초 시험 6초, 30분 시험 8초).
5. 연결을 닫고 `POST /api/v1/sessions/{id}/end`로 세션을 끝낸다.
6. 받은 메시지의 `utterances[].kind`별 개수를 센다. `late_archive_final`이 늦은 확정이다.

### 5.3 100초 스트림 시험

- 먼저 stream_02를 한 번 재생해 예열한다 (라벨 `main_merged_warmup`). 첫 재생은 모델 첫 호출 때문에 늦은 확정이 생길 수 있어 결과에서 뺀다.
- 그다음 stream_00~05를 한 세션씩 차례로 재생한다 (라벨 `main_merged_workers2`). 세션 사이 서버 재시작은 없다.
- 각 스트림 뒤 `nvidia-smi`로 GPU 메모리를 기록한다.
- 6개가 끝난 뒤 `GET /api/v1/runtime/monitor`의 `audio_pipeline`을 읽는다.

### 5.4 30분 연속 시험

- 새로 띄운 서버에서 stream_02로 예열한 뒤 `long_session_eval.py 3 main_merged_30min`을 실행한다.
- 재생하는 동안 60초마다 아래를 기록한다.
  - `GET /api/v1/runtime/monitor`의 `average_queue_delay_ms`, `max_queue_delay_ms`, `backpressure_count`, `error_count`
  - 서버 프로세스 메모리: 8011 포트를 LISTEN하는 PID의 `WorkingSet64`
  - GPU 메모리: `nvidia-smi --query-gpu=memory.used`
  - 지금까지 받은 확정 수와 늦은 확정 수
- 모니터 수치는 최근 확정 120개 기준이다(`RuntimeMonitorService` 기본값). 1분에 확정이 약 8개 나오므로 모든 확정이 적어도 한 번은 집계 범위에 들어간다.

### 5.5 지표 정의

| 지표 | 정의 |
|---|---|
| 확정 작업 대기 시간 (`final_queue_delay_ms`) | 확정 작업을 처리하기 시작한 시각 − 그 구간이 끝난 시각. 3,500ms를 넘으면 그 확정은 `late_archive_final`로 강등된다 |
| 회색→확정 교체 시간 (`live_final_delay_ms`) | 같은 구간의 `archive_final`을 보낸 시각 − 그 구간의 회색 `live_final`을 보낸 시각 |
| 백프레셔 | 확정 작업 대기 시간이 설정값을 넘어 회색 자막 생성을 잠시 멈춘 횟수 (`StreamAlignmentManager.apply_final_queue_delay`) |

## 6. 결과

### 6.1 100초 스트림 6개

| 스트림 | 길이(초) | 확정 수 | 늦은 확정 | CER | 정확도 |
|---|---|---|---|---|---|
| stream_00 | 99.0 | 15 | 0 | 0.1101 | 89.0% |
| stream_01 | 99.3 | 12 | 0 | 0.1108 | 88.9% |
| stream_02 | 93.8 | 14 | 0 | 0.1003 | 90.0% |
| stream_03 | 106.3 | 13 | 0 | 0.0812 | 91.9% |
| stream_04 | 100.8 | 13 | 0 | 0.0487 | 95.1% |
| stream_05 | 111.6 | 17 | 0 | 0.0573 | 94.3% |
| 평균 | | 14.0 | 0 | 0.0847 | **91.5%** |

평균은 스트림별 CER의 단순 평균이다. 예열 실행(stream_02)도 CER 0.1003, 늦은 확정 0개로 본 실행과 같았다.

6개가 끝난 뒤 모니터 값 (예열 포함 확정 98개 기준):

| 항목 | 값 |
|---|---|
| 확정 작업 대기 시간 | 평균 0ms, 최대 0ms |
| 늦은 확정 | 0 |
| 백프레셔 | 0 |
| 오류 | 0 |
| 회색→확정 교체 시간 | 평균 901ms |
| GPU 메모리 | 6개 내내 3,142MB |
| 서버 로그의 LLM 인사이트 호출 | 0회 |

### 6.2 수정 전 main과 비교 (같은 방식, 같은 스트림)

| 스트림 | 수정 전 main CER | 현재 main CER |
|---|---|---|
| stream_00 | 0.2232 (77.7%) | 0.1101 (89.0%) |
| stream_01 | 0.2902 (71.0%) | 0.1108 (88.9%) |

수정 전 main은 stream_00, 01 두 개만 쟀다. 확정 수가 36·40개로 현재(15·12개)보다 훨씬 많다. 최대 구간 1.8초 때문에 말 중간을 끊었기 때문이다.

### 6.3 30분 연속

| 경과(분) | 확정 수 | 늦은 확정 | 대기 평균 / 최대(ms) | 백프레셔 | 오류 | 서버 메모리(MB) | GPU 메모리(MB) |
|---|---|---|---|---|---|---|---|
| 5 | 40 | 0 | 0 / 0 | 0 | 0 | 1,029.7 | 3,142 |
| 10 | 80 | 0 | 0 / 0 | 0 | 0 | 1,051.0 | 3,142 |
| 15 | 123 | 0 | 0 / 0 | 0 | 0 | 1,051.1 | 3,142 |
| 20 | 164 | 0 | 0 / 0 | 0 | 0 | 1,051.0 | 3,142 |
| 25 | 209 | 0 | 0 / 0 | 0 | 0 | 1,051.2 | 3,142 |
| 30 | 249 | 0 | 0 / 0 | 0 | 0 | 1,051.2 | 3,142 |
| 31 (끝) | 256 | 0 | 0 / 0 | 0 | 0 | 1,051.3 | 3,142 |

- 전체: 30.8분, 확정 256개, 늦은 확정 0개, CER **0.0791 (정확도 92.1%)**
- 메시지 수: `preview` 1,810, `live_final` 1,973, `archive_final` 256
- 60초 간격 31번 기록 모두 대기 최대 0ms였다. 서버 메모리는 최소 1,025.9MB, 최대 1,051.3MB다.
- 첫 시도는 20분 시점에 PC 전체 메모리가 부족해 Claude Code가 백그라운드 서버를 종료시켜 중단됐다. 그때까지 수치는 위와 같은 추세였다. 표는 사용자가 직접 터미널에서 다시 돌린 두 번째 실행 결과다.

## 7. 오프라인 평가에서 가져온 값

실서버에서 직접 재지 않은 값은 [파이프라인 평가](실시간_STT_파이프라인_평가.md)의 같은 설정 결과를 쓴다.

| 항목 | 값 | 출처 |
|---|---|---|
| 말이 끝난 뒤 확정까지 (Silero 300ms, 최대 12초, 잡음 없음) | 평균 300ms, p90 440ms | 5.11 |
| 같은 조건, SNR 10dB 분홍 잡음 | CER 0.091 (90.9%), p90 500ms | 5.11 |
| 수정 전 제품 설정, SNR 10dB | CER 0.495 (50.5%) | 5.11 |
| 회색 자막 sherpa 단독 (FLEURS 40개, 피크 정규화) | CER 0.210 (79.0%) | 5.1, 5.2 |
| 회색 자막 Nemotron 단독 (2단계 후보) | CER 0.085 (91.5%) | 5.1 |

## 8. 한계

- 정답이 있는 낭독 음성(FLEURS)이다. 끊기고 겹치는 실제 회의 대화에서는 정확도가 더 낮을 수 있다.
- 6개 스트림은 서로 다른 클립 27개로 만들었고, 30분 시험은 같은 6개를 3번 반복한 것이다. 문장 다양성이 넓지 않다.
- 스크립트가 WebSocket으로 PCM을 보낸 것이다. Tauri 오버레이의 시스템 오디오 캡처(루프백)와 화면 표시는 거치지 않았다.
- 말이 끝난 순간부터 확정 자막이 클라이언트에 닿기까지의 끝단 지연은 실서버에서 직접 재지 않았다. 7장의 오프라인 값으로 대신한다.
- 회색 자막 정확도와 첫 글자 지연은 실서버에서 재지 않았다.
- 세션은 한 번에 하나만 돌렸다. 동시 세션 2개 이상은 재지 않았다.
- `system_audio` 프로필만 쟀다. `mic`, `mic_and_audio`도 Silero로 바꿨지만 실제 마이크 입력으로는 돌리지 않았다.
- 비동기 실시간 질문 경로(`LIVE_QUESTION_ANALYSIS_ENABLED=true`)는 켜지 않았다.
- 같은 PC에서 다른 프로그램이 GPU를 쓰는 조건은 재지 않았다.

## 9. 재현 방법

스크립트는 저장소 밖 `D:\stt_eval`에 있고, 결과는 `D:\stt_eval\results`에 쌓인다.

| 파일 | 역할 |
|---|---|
| `prep_fleurs.py` | FLEURS 40개 추출 → `fleurs\manifest.json` |
| `build_streams.py` | 스트림 6개 생성 → `streams\stream_XX.wav`, `streams\manifest.json` |
| `bench.py` | WAV 로더, `normalize()`, `cer()` |
| `e2e_ws_eval.py <스트림 번호> <라벨>` | 100초 스트림 실서버 재생 → `results\e2e_ws.jsonl`에 한 줄 추가 |
| `long_session_eval.py <반복 수> <라벨>` | 연속 재생 + 60초 간격 기록 → `results\long_session_<라벨>.json` |

```powershell
# 서버는 5.1처럼 띄운 상태에서
cd D:\stt_eval
$env:PYTHONIOENCODING="utf-8"
$py = "D:\meeting-overlay-assistant\venv\Scripts\python.exe"
& $py e2e_ws_eval.py 2 warmup
0..5 | % { & $py e2e_ws_eval.py $_ main_merged_workers2 }
& $py long_session_eval.py 3 main_merged_30min
```

## 10. 다음에 잴 것

1. Tauri 오버레이 실기: 시스템 오디오 캡처부터 화면 표시까지, 끝단 지연 포함
2. 동시 세션 2개의 지연과 늦은 확정 수. 결과에 따라 `LIVE_STREAM_MAX_RUNNING_SESSIONS`(현재 4)를 2로 낮출지 정한다
3. `mic` 프로필 실제 마이크 입력
4. 비동기 실시간 질문 경로 (Redis + live-question 워커)
5. ~~2단계: 회색 자막을 Nemotron으로 바꾼 뒤 같은 절차로 다시 측정~~ 완료: [회색 자막 Nemotron 전환 실서버 검증](실시간_STT_회색자막_Nemotron_검증.md)
