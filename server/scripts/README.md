# server/scripts

서버 전용 지원 스크립트와 내부 작업 도구 모음입니다.

이 폴더는 사람이 가장 먼저 들어오는 위치가 아닙니다. 평소 실행은 [`scripts`](../../scripts/README.md)에서 시작하고, 서버 전용 구현을 수정하거나 확장할 때만 여기로 내려옵니다.

## 구조

```text
server/scripts/
├─ admin/
│  └─ setup_server.py
├─ audio/
│  ├─ stream_live_audio_ws.ps1
│  ├─ stream_live_audio_ws.py
│  ├─ run_audio_ws_e2e.ps1
│  ├─ run_audio_ws_e2e.py
│  └─ send_text_chunk.py
├─ env/
│  ├─ install_ryzenai_runtime.ps1
│  ├─ rebuild_main_env.ps1
│  ├─ setup_diarization_worker_env.ps1
│  └─ verify_ryzenai_npu.ps1
├─ workers/
│  └─ pyannote_worker.py
├─ build/
│  └─ build_overlay.ps1
└─ testing/
   └─ run_tests.ps1
```

## 폴더 역할

### `admin/`

운영 콘솔과 관리 CLI 본체입니다.

- `setup_server.py`
  - `dashboard`
  - `doctor`
  - `logs`
  - `settings`
  - `profiles`
  - 멤버 관리
  - 초기 관리자 생성

### `audio/`

실시간 오디오/텍스트 입력 경로를 점검합니다.

- `stream_live_audio_ws.*`: 마이크 또는 시스템 오디오를 WebSocket으로 전송
- `run_audio_ws_e2e.*`: WAV 파일 기반 오디오 E2E 점검
- `send_text_chunk.py`: 텍스트 WebSocket 테스트

### `env/`

환경 구성과 런타임 설치용입니다.

- `install_ryzenai_runtime.ps1`
- `rebuild_main_env.ps1`
- `setup_diarization_worker_env.ps1`
- `verify_ryzenai_npu.ps1`

### `workers/`

별도 프로세스나 별도 venv에서 실행하는 worker 본체입니다.

- `pyannote_worker.py`

### `build/`

빌드 보조 스크립트입니다.

- `build_overlay.ps1`

### `testing/`

개발 보조 테스트 진입점입니다.

- `run_tests.ps1`

## 루트 `scripts`와의 관계

사람이 직접 치는 명령은 루트 [`scripts`](../../scripts/README.md)에 있습니다.

- `scripts/server-admin.ps1` -> `admin/setup_server.py`
- `scripts/live-audio.ps1` -> `audio/stream_live_audio_ws.ps1`
- `scripts/audio-e2e.ps1` -> `audio/run_audio_ws_e2e.ps1`
- `scripts/send-text.ps1` -> `audio/send_text_chunk.py`

즉, 루트 `scripts/`는 실행 입구이고 `server/scripts/`는 서버 내부 본체입니다.
