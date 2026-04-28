# scripts

루트 `scripts/`는 프로젝트의 공식 실행 진입점 모음입니다.
실행은 여기서 시작하고, 내부 구현이 필요할 때만 하위 스크립트로 내려갑니다.

## 구조 원칙

1. 루트 `scripts/*.ps1`는 사람이 직접 치는 공식 진입점만 둡니다.
2. 실제 구현은 `scripts/dev`, `scripts/audio`, `scripts/admin`, `scripts/data`, `scripts/bench` 아래에 둡니다.
3. 루트 파일은 가능하면 thin wrapper만 유지합니다.
4. 서버 내부 본체는 `server/scripts/` 아래에 둡니다.

## 주요 스크립트

### `dev-server.ps1`

FastAPI 서버를 실행합니다.
기본값은 통합 서버이고, `-EntryPoint`로 control/live를 분리해서 띄울 수 있습니다.

```powershell
.\scripts\dev-server.ps1
.\scripts\dev-server.ps1 -EntryPoint server.app.entrypoints.control_api:app
.\scripts\dev-server.ps1 -Port 8012 -EntryPoint server.app.entrypoints.live_api:app
```

### `dev-client.ps1`

클라이언트를 실행합니다.
기본값은 overlay이고, `-Target web`으로 web workspace를 띄울 수 있습니다.

```powershell
.\scripts\dev-client.ps1
.\scripts\dev-client.ps1 -Target web
.\scripts\dev-client.ps1 -Target web -BuildOnly
```

### `dev-stack.ps1`

앱 전체 개발 스택을 한 번에 실행합니다.
기본값은 `control server + live server + report worker + overlay + web`입니다.
실시간 STT와 일반 API를 분리한 split 개발 스택이 기본값입니다.

```powershell
.\scripts\dev-stack.ps1
.\scripts\dev-stack.ps1 -SkipWeb
.\scripts\dev-stack.ps1 -SkipOverlay
.\scripts\dev-stack.ps1 -SkipReportWorker
.\scripts\dev-stack.ps1 -Preview
```

### `dev-infra.ps1`

개발용 PostgreSQL + Redis 인프라를 한 번에 관리합니다.
기본값은 둘 다 올리고, 필요하면 `-Service postgresql` 또는 `-Service redis`로 좁힐 수 있습니다.

```powershell
.\scripts\dev-infra.ps1 up
.\scripts\dev-infra.ps1 -Action logs
.\scripts\dev-infra.ps1 -Action status
.\scripts\dev-infra.ps1 -Action psql
.\scripts\dev-infra.ps1 -Action redis-cli
```

### `dev-postgres.ps1`

기존 PostgreSQL 전용 진입점 호환 wrapper입니다.

```powershell
.\scripts\dev-postgres.ps1 up
.\scripts\dev-postgres.ps1 logs
```

### `dev-redis.ps1`

기존 Redis 전용 진입점 호환 wrapper입니다.
report generation worker가 queue wake-up 신호를 받을 때 사용합니다.

```powershell
.\scripts\dev-redis.ps1 up
.\scripts\dev-redis.ps1 logs
```

### `dev-report-worker.ps1`

report generation worker를 별도 프로세스로 실행합니다.
통합 서버나 control API와 같이 돌릴 때 쓰는 스크립트입니다.

```powershell
.\scripts\dev-report-worker.ps1
.\scripts\dev-report-worker.ps1 -Once
```

### `dev-live-question-worker.ps1`

실시간 질문 분석 worker를 별도 프로세스로 실행합니다.
question-only live event lane을 켰을 때 Redis request/result stream을 소비합니다.
MVP 기본값은 `LIVE_QUESTION_ANALYSIS_ENABLED=false`이므로 이 worker는 시작하지 않습니다.

```powershell
.\scripts\dev-live-question-worker.ps1
.\scripts\dev-live-question-worker.ps1 -Once
```

### `dev-note-correction-worker.ps1`

note correction / workspace summary worker를 별도 프로세스로 실행합니다.
summary 생성이나 note correction queue를 직접 점검할 때 사용합니다.

```powershell
.\scripts\dev-note-correction-worker.ps1
.\scripts\dev-note-correction-worker.ps1 -Once
```

### `benchmark-live-questions.ps1`

실시간 질문 감지 모델을 오프라인 데이터셋으로 비교합니다.
MVP 기본 기능 검증이 아니라, 추후 실험 기능을 다시 켤 때 사용하는 벤치입니다.
기본값은 `tests/fixtures/support/live_questions_benchmark_v1.json`이고, backend/model/base URL은 `.env` 값을 그대로 따릅니다.

```powershell
.\scripts\benchmark-live-questions.ps1
.\scripts\benchmark-live-questions.ps1 -Model qwen2.5:3b-instruct
.\scripts\benchmark-live-questions.ps1 -Output json -SaveJson .\artifacts\live-question-benchmark.json
```

### `run-live-stt-candidate-batch.ps1`

live STT 후보 backend를 manifest 기준으로 배치 비교합니다.
streaming 후보를 빠르게 훑을 때 쓰는 실험 진입점입니다.

```powershell
.\scripts\run-live-stt-candidate-batch.ps1
.\scripts\run-live-stt-candidate-batch.ps1 -Source mic -Limit 10 -Warmup
```

### `run-note-stt-candidate-matrix.ps1`

note/final STT 후보 조합을 manifest 기준으로 매트릭스 실행합니다.
배치형 정확도 비교 실험 진입점입니다.

```powershell
.\scripts\run-note-stt-candidate-matrix.ps1
.\scripts\run-note-stt-candidate-matrix.ps1 -IncludeMoonshine
```

### Ollama 기능별 모델 프로필

회의록, 노트 인사이트, 챗봇, 실시간 질문 감지처럼 용도가 다른 LLM 호출은 alias 모델을 나눠서 관리합니다.
처음 한 번만 아래 스크립트를 실행하면 필요한 기본 모델 pull과 alias 생성이 같이 처리됩니다.

```powershell
.\scripts\create-ollama-profiles.ps1
```

개별로 만들 때는 아래 명령을 사용합니다.

```powershell
ollama create caps-meeting-minutes-gemma4 -f .\server\config\ollama\Modelfile.meeting-minutes-gemma4-e4b
ollama create caps-note-insight-gemma4 -f .\server\config\ollama\Modelfile.note-insight-gemma4-e4b
ollama create caps-assistant-qwen7b -f .\server\config\ollama\Modelfile.assistant-qwen2.5-7b
ollama create caps-live-question-qwen3b -f .\server\config\ollama\Modelfile.live-question-qwen2.5-3b
```

### `server-admin.ps1`

운영용 CLI/TUI 진입점입니다.

```powershell
.\scripts\server-admin.ps1 dashboard
.\scripts\server-admin.ps1 doctor
.\scripts\server-admin.ps1 logs --lines 30
```

### `live-audio.ps1`

마이크나 시스템 오디오를 WebSocket으로 전송합니다.

```powershell
.\scripts\live-audio.ps1 -Source system_audio
```

### `audio-e2e.ps1`

WAV 파일 기반 오디오 WebSocket 경로를 확인합니다.

```powershell
.\scripts\audio-e2e.ps1 -WavPath .\artifacts\sample.wav
```

### `send-text.ps1`

텍스트 WebSocket 테스트 메시지를 전송합니다.

```powershell
.\scripts\send-text.ps1 123e4567-e89b-12d3-a456-426614174000 hello meeting start
```

## 메모

1. 루트 `scripts/`를 공식 진입점으로 사용합니다.
2. 현재 구조 기준은 `client/overlay`, `client/web`, `server`입니다.
3. 개발용 인프라는 `dev-infra.ps1`가 대표 진입점입니다.
4. `server/scripts/`는 서버 전용 내부 구현과 도구 모음입니다.
