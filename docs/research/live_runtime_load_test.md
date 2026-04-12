# Live Runtime 부하 테스트

## 목적

이 문서는 `LiveStreamContext -> InferenceScheduler -> STTWorkerPool` 구조가
동시 세션 수와 worker 수에 따라 어떻게 반응하는지 빠르게 확인한 기록이다.

이번 테스트의 목적은 다음 두 가지다.

1. `worker=1`과 `worker=2`가 synthetic 부하에서 얼마나 차이 나는지 본다.
2. 현재 정책이 `preview`보다 `final`을 얼마나 잘 보호하는지 본다.

이 문서는 정확도 벤치마크가 아니다.
실제 STT backend 품질이나 WER/CER을 재는 문서가 아니라,
`runtime queue / scheduler / worker` 구조가 어디서 밀리는지 보는 문서다.

## 측정 시점

- 일시: 2026-03-14 KST
- 코드 기준: `live runtime` 2차
- 관련 스크립트:
  - `server/experiments/stt/benchmark_live_stream_runtime.py`

## 테스트 환경

- OS: Windows
- 실행 환경: `D:\caps\venv`
- 하드웨어:
  - GPU: RTX 5070
  - RAM: 32GB
- 특이사항:
  - 서버/클라이언트를 같은 노트북에서 개발/검증하는 전제를 둔다.
  - 이번 테스트는 실제 마이크/시스템 오디오 대신 synthetic text chunk를 사용한다.
  - pipeline은 synthetic preview/final latency를 갖는 fake pipeline으로 대체했다.

## 테스트 시나리오

### 입력 조건

- 세션 수: `1, 2, 4, 8`
- worker 수: `1, 2`
- 세션당 chunk 수: `10`
- chunk 전송 간격: `20ms`
- preview 처리 지연: `8ms`
- final 처리 지연: `60ms`
- 스트림당 pending final 큐 길이: `3`

### 측정 항목

- `elapsed_s`
- `preview_p50`, `preview_p95`
- `final_p50`, `final_p95`
- `preview_rate`
- `final_rate`
- `max_pending`
- `coalesced`
- `busy_workers`

## 실행 명령

```powershell
D:\caps\venv\Scripts\python.exe D:\caps\server\experiments\stt\benchmark_live_stream_runtime.py `
  --sessions 1,2,4,8 `
  --workers 1,2 `
  --chunks-per-session 10 `
  --chunk-interval-ms 20 `
  --preview-latency-ms 8 `
  --final-latency-ms 60 `
  --pending-per-stream 3 `
  --max-running-streams 16
```

## 결과

| workers | sessions | elapsed_s | preview_p50_ms | preview_p95_ms | final_p50_ms | final_p95_ms | preview_rate | final_rate | max_pending | coalesced | busy_workers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 0.38 | 10.79 | 10.79 | 190.20 | 219.61 | 10.00% | 100.00% | 4 | 12 | 1 |
| 1 | 2 | 0.56 | 12.88 | 16.74 | 340.35 | 424.54 | 10.00% | 100.00% | 8 | 27 | 1 |
| 1 | 4 | 0.94 | 17.41 | 24.95 | 634.55 | 769.63 | 7.50% | 100.00% | 16 | 58 | 1 |
| 1 | 8 | 1.61 | 18.07 | 25.70 | 1233.26 | 1508.14 | 3.75% | 100.00% | 32 | 123 | 1 |
| 2 | 1 | 0.38 | 8.83 | 8.83 | 205.70 | 244.65 | 10.00% | 100.00% | 4 | 12 | 1 |
| 2 | 2 | 0.38 | 9.76 | 9.80 | 195.34 | 226.56 | 10.00% | 100.00% | 8 | 24 | 2 |
| 2 | 4 | 0.57 | 9.43 | 17.18 | 344.75 | 418.39 | 7.50% | 100.00% | 16 | 55 | 2 |
| 2 | 8 | 0.87 | 13.52 | 18.15 | 631.98 | 811.07 | 5.00% | 100.00% | 32 | 120 | 2 |

## 해석

### 1. 현재 정책은 `final` 보호에 성공한다

- 모든 시나리오에서 `final_rate`가 `100%`였다.
- 즉 현재 구조는 preview를 희생해도 final 결과는 끝까지 내보내는 방향으로 동작한다.

### 2. `worker=1`은 4세션 이후 final latency가 빠르게 오른다

- `worker=1`, `sessions=4`에서 `final_p95`는 약 `770ms`
- `worker=1`, `sessions=8`에서 `final_p95`는 약 `1508ms`

같은 머신에서 여러 live 세션을 붙이면 `worker=1`은 금방 보수적인 한계에 도달한다.

### 3. `worker=2`는 synthetic 기준으로 확실히 이득이 있다

- `sessions=8` 기준
  - `worker=1`: `final_p95` 약 `1508ms`
  - `worker=2`: `final_p95` 약 `811ms`

즉 synthetic workload에서는 `worker=2`가 final latency를 꽤 의미 있게 낮췄다.

### 4. 병목은 네트워크보다 runtime queue 쪽이다

- 세션 수가 늘수록 `max_pending`, `coalesced`가 같이 증가했다.
- 이 결과는 현재 병목이 `오디오 전송`이 아니라
  `stream context backlog -> scheduler -> worker` 경로 쪽에 있다는 걸 보여준다.

### 5. preview는 의도적으로 덜 보호된다

- `preview_rate`는 세션 수가 늘수록 떨어졌다.
- 이건 현재 정책이 `preview`보다 `final`을 우선하는 구조라서 정상이다.

## 현재 결론

### 지금 말할 수 있는 것

- 구조 방향은 맞다.
- `세션별 상태 분리 + fair scheduling + shared worker`는 실제로 동작한다.
- `worker=2`는 최소한 synthetic 환경에서는 값이 있다.

### 아직 말할 수 없는 것

- 실제 faster-whisper backend에서도 `worker=2`가 안전한지는 아직 확정할 수 없다.
- 실제 모델 경로에서는 model cache, GPU 메모리, backend thread safety 영향이 들어간다.
- 따라서 synthetic 결과를 곧바로 production 설정값으로 쓰면 안 된다.

## 권장 다음 단계

## 후속 actual backend 측정

- 같은 구조를 실제 backend에 붙인 후속 결과는
  [live runtime actual backend 부하 테스트](live_runtime_actual_backend_load_test.md)에 정리했다.
- 결론은 synthetic에서 보였던 `worker=2` 이점이
  현재 same-machine actual backend에서는 재현되지 않았다는 쪽이다.

## 권장 다음 단계

1. `queue delay`, `late_final`, `backpressure`, `preview_drop`를 같이 본다.
2. dedicated server 환경에서 `worker=1`, `worker=2`를 다시 비교한다.
3. 그 결과를 바탕으로 기본값을 정한다.

## 운영 판단 메모

- 개발 기본값은 여전히 `worker=1`이 안전하다.
- 실제 server settings에서 worker 수를 조절할 수 있게 열어두되,
  기본 preset은 backend 검증 전까지 보수적으로 유지하는 게 맞다.
- synthetic 테스트는 구조 검증용,
  actual backend 테스트는 운영값 결정용으로 분리해서 봐야 한다.
