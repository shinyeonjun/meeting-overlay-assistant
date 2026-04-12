# Live Runtime Actual Backend 부하 테스트

## 목적

이 문서는 synthetic pipeline으로 구조만 검증한
[live runtime 부하 테스트](live_runtime_load_test.md) 다음 단계다.

이번 측정의 목적은 아래 두 가지다.

1. 현재 설정된 실제 STT backend를 `LiveStreamContext -> InferenceScheduler -> STTWorkerPool` 경로에 직접 붙였을 때
   `worker=1`과 `worker=2`가 어떻게 달라지는지 본다.
2. synthetic 테스트에서 보였던 `worker=2` 이점이 같은 머신의 actual backend에서도 유지되는지 확인한다.

## 측정 시점

- 일시: 2026-03-14 KST
- 기준 코드: `preview/final` job 분리 + draining/coalescing 지표 반영 이후

## 테스트 환경

- OS: Windows
- 실행 환경: `D:\caps\venv`
- 하드웨어
  - GPU: RTX 5070
  - RAM: 32GB
- 실행 형태
  - 서버/클라이언트를 같은 노트북에서 개발/검증하는 상황을 가정했다.
  - actual runtime benchmark는 `same-machine` 기준이다.

## 측정 범위

이번 측정은 `실제 STT backend + 실제 AudioPipelineService + 실제 LiveStreamService` 경로를 본다.
다만 아래 항목은 intentionally 빼서 STT/runtime 지연만 보도록 했다.

- analyzer는 no-op
- utterance/event 저장소는 no-op
- report/refiner/post-processing은 제외

즉 이 문서는 `실제 backend가 붙었을 때 runtime scheduler/worker 정책이 어떤지`를 보는 문서지,
최종 제품 전체 E2E 지연을 재는 문서는 아니다.

## 현재 settings 기준 backend

이번 머신의 현재 설정은 아래와 같았다.

- `mic`
  - backend: `faster_whisper_streaming`
- `system_audio`
  - backend: `hybrid_local_streaming`

참고로 두 프로파일 모두 이번 측정 시점에는 `shared_instance=false`였다.
즉 같은 source에서 세션이 늘어나면 shared singleton 하나를 같이 쓰는 구조가 아니라,
세션별 pipeline이 각각 STT service를 만들고 runtime worker가 그 호출 시점을 조절하는 형태였다.

## 실행 스크립트

- 스크립트: [benchmark_live_stream_runtime_actual.py](/D:/caps/server/experiments/stt/benchmark_live_stream_runtime_actual.py)

### mic backend 측정 명령

```powershell
D:\caps\venv\Scripts\python.exe D:\caps\server\experiments\stt\benchmark_live_stream_runtime_actual.py `
  --source mic `
  --sessions 1,2,4 `
  --workers 1,2 `
  --chunk-ms 250 `
  --chunk-interval-ms 40 `
  --pending-per-stream 3 `
  --max-running-streams 8 `
  --warmup `
  --output-json temp\benchmark_live_runtime_actual_mic.json
```

### system audio backend 측정 명령

```powershell
D:\caps\venv\Scripts\python.exe D:\caps\server\experiments\stt\benchmark_live_stream_runtime_actual.py `
  --source system_audio `
  --sessions 1,2 `
  --workers 1,2 `
  --chunk-ms 250 `
  --chunk-interval-ms 40 `
  --pending-per-stream 3 `
  --max-running-streams 8 `
  --warmup `
  --output-json temp\benchmark_live_runtime_actual_system_audio.json
```

## 결과

### mic / `faster_whisper_streaming`

| workers | sessions | elapsed_s | first_preview_p50_ms | first_preview_p95_ms | first_final_p50_ms | first_final_p95_ms | terminal_p50_ms | terminal_p95_ms | preview_emit | final_emit | max_pending | coalesced | busy_workers | errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 2.45 | 1228.74 | 1228.74 | 579.64 | 579.64 | 2448.42 | 2448.42 | 2 | 8 | 4 | 92 | 1 | 0 |
| 1 | 2 | 3.71 | 386.26 | 386.26 | 698.30 | 788.58 | 3610.83 | 3700.25 | 1 | 16 | 8 | 210 | 1 | 0 |
| 1 | 4 | 7.01 | 390.34 | 390.34 | 899.51 | 1183.45 | 6515.96 | 6983.00 | 1 | 32 | 16 | 435 | 1 | 0 |
| 2 | 1 | 2.43 | 1832.21 | 1832.21 | 781.74 | 781.74 | 2434.09 | 2434.09 | 1 | 8 | 4 | 97 | 1 | 0 |
| 2 | 2 | 4.05 | - | - | 1156.27 | 1170.64 | 4042.48 | 4052.61 | 0 | 16 | 8 | 218 | 2 | 0 |
| 2 | 4 | 7.38 | 751.74 | 764.39 | 1373.69 | 2642.94 | 6758.99 | 7316.05 | 2 | 32 | 16 | 445 | 2 | 0 |

### system audio / `hybrid_local_streaming`

| workers | sessions | elapsed_s | first_preview_p50_ms | first_preview_p95_ms | first_final_p50_ms | first_final_p95_ms | terminal_p50_ms | terminal_p95_ms | preview_emit | final_emit | max_pending | coalesced | busy_workers | errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 3.58 | 1547.56 | 1547.56 | 1774.31 | 1774.31 | 3578.57 | 3578.57 | 2 | 8 | 4 | 62 | 1 | 0 |
| 1 | 2 | 6.27 | 3010.00 | 3017.06 | 3343.60 | 3430.24 | 6265.72 | 6265.91 | 2 | 16 | 8 | 185 | 1 | 0 |
| 2 | 1 | 3.65 | 1599.69 | 1599.69 | 1843.60 | 1843.60 | 3649.42 | 3649.42 | 1 | 8 | 4 | 67 | 1 | 0 |
| 2 | 2 | 6.24 | 3018.42 | 3018.80 | 3448.29 | 3468.11 | 6225.64 | 6236.38 | 2 | 16 | 8 | 182 | 2 | 0 |

## 해석

### 1. synthetic에서 보였던 `worker=2` 이점이 actual backend에서는 재현되지 않았다

synthetic 결과만 보면 `worker=2`가 final latency를 의미 있게 낮췄다.
하지만 actual backend에서는 같은 결론이 안 나왔다.

- `mic`, `sessions=2`
  - `worker=1`: `first_final_p95` 약 `788.58ms`
  - `worker=2`: `first_final_p95` 약 `1170.64ms`
- `mic`, `sessions=4`
  - `worker=1`: `first_final_p95` 약 `1183.45ms`
  - `worker=2`: `first_final_p95` 약 `2642.94ms`

즉 현재 `faster_whisper_streaming` 기준 same-machine actual 경로에서는
`worker=2`가 오히려 더 불리했다.

### 2. system audio `hybrid_local_streaming`도 `worker=2`가 거의 이득이 없었다

- `sessions=2`
  - `worker=1`: `first_final_p95` 약 `3430.24ms`
  - `worker=2`: `first_final_p95` 약 `3468.11ms`

terminal latency도 사실상 비슷했다.
즉 hybrid 경로에서도 이번 머신 기준으로는 worker를 2로 늘릴 이유가 약했다.

### 3. preview emit 수는 매우 희소했고, 운영 판단 기준은 final latency가 더 중요했다

- `mic` 경로에서도 preview emit이 세션 수가 늘수록 거의 사라졌다.
- `system_audio` 경로도 preview emit은 적고 첫 preview 지연이 컸다.

이 결과는 현재 runtime 정책이 `preview`보다 `final`을 우선하고 있다는 점과도 맞는다.
운영값을 정할 때는 preview 개수보다 `first_final`, `terminal`, `coalesced`를 먼저 보는 게 맞다.

### 4. 병목은 여전히 runtime backlog와 coalescing에서 드러났다

- 세션 수가 늘수록 `max_pending`, `coalesced`가 같이 커졌다.
- `mic`, `sessions=4`에서는 `coalesced`가 `435~445`
- `system_audio`, `sessions=2`에서는 `coalesced`가 `182~185`

즉 network보다 `pending buffer -> scheduler -> worker -> backend` 경로가 지연의 핵심이다.

### 5. 현재 프로파일은 `shared_instance=false`라서, worker를 늘려도 같은 모델 공유 최적화로 바로 이어지지 않는다

이번 측정 시점 프로파일 기준:

- `mic`: `faster_whisper_streaming`, `shared_instance=false`
- `system_audio`: `hybrid_local_streaming`, `shared_instance=false`

즉 worker를 늘렸다고 해서 같은 singleton 모델 하나를 더 효율적으로 쓰는 상황이 아니었다.
실제로는 세션별 service 생성과 GPU/CPU contention이 같이 붙기 때문에,
same-machine dev 환경에서는 worker 증가가 성능 개선으로 바로 이어지지 않았다.

## synthetic 대비 비교 요약

| 시나리오 | synthetic 결론 | actual 결론 |
| --- | --- | --- |
| `mic`, worker 1 -> 2, sessions 4 | final latency 개선 | final latency 악화 |
| `system_audio`, worker 1 -> 2, sessions 2 | synthetic 없음 | 거의 변화 없음 |
| 구조 검증 관점 | `worker=2` 가능성 확인 | 현재 backend/profile에선 기본값으로 쓰기 위험 |

정리하면:

- synthetic는 구조 가능성 검증용
- actual은 현재 운영값 결정용

이 둘을 같은 의미로 해석하면 안 된다.

## 현재 결론

### 지금 말할 수 있는 것

- 현재 same-machine actual backend 기준으로는 `worker=1`이 안전한 기본값이다.
- `worker=2`는 이 머신과 현재 profile 조합에서는 이점이 없거나 오히려 더 나빴다.
- 따라서 server settings에 worker 수를 열어두더라도 기본 preset은 `1`로 유지하는 게 맞다.

### 아직 남은 것

- dedicated server 환경에서 같은 테스트를 다시 돌려야 한다.
- `shared_instance=true` 또는 batching 가능한 backend/profile로 바뀌면 결론이 달라질 수 있다.
- `queue delay`, `preview_drop_count`, `late_final`까지 같이 보면 더 정확하다.

## 권장 다음 단계

1. `runtime monitor`에 `preview_drop_count`, `queue_delay_ms`를 추가한다.
2. 전용 서버 환경에서 `worker=1`, `worker=2`를 다시 측정한다.
3. backend/profile별로 `shared_instance` 정책을 다시 점검한다.
4. `worker` 설정을 dashboard/settings에서 조절 가능하게 열되, 기본값은 `1`로 유지한다.
