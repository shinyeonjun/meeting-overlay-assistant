# scripts

프로젝트 전체에서 직접 실행하는 공식 entrypoint 모음입니다.

핵심 원칙은 단순합니다.

- `scripts/`는 사람이 직접 실행하는 루트 명령입니다.
- `server/scripts/`는 서버 전용 본체와 지원 도구입니다.
- 평소에는 `scripts/`만 기억하고, 구현을 고칠 때만 `server/scripts/`로 내려갑니다.

## 구조

```text
scripts/
├─ common/
│  └─ _console_utf8.ps1
├─ dev-stack.ps1
├─ dev-server.ps1
├─ dev-client.ps1
├─ server-admin.ps1
├─ live-audio.ps1
├─ audio-e2e.ps1
├─ send-text.ps1
└─ README.md
```

## 역할

### `dev-stack.ps1`

서버와 클라이언트를 같이 실행합니다. 로컬 수동 QA를 시작할 때 가장 먼저 쓰는 진입점입니다.

```powershell
.\scripts\dev-stack.ps1
.\scripts\dev-stack.ps1 -Preview
```

### `dev-server.ps1`

FastAPI 서버만 실행합니다. `.env`의 `SERVER_HOST`, `SERVER_PORT`를 우선 사용합니다.

```powershell
.\scripts\dev-server.ps1
```

### `dev-client.ps1`

Tauri 클라이언트만 실행합니다.

```powershell
.\scripts\dev-client.ps1
```

### `server-admin.ps1`

운영자용 CLI/TUI 진입점입니다. 설치, 진단, 로그, 설정, 프로필을 여기서 시작합니다.

```powershell
.\scripts\server-admin.ps1 dashboard
.\scripts\server-admin.ps1 doctor
.\scripts\server-admin.ps1 logs --lines 30
.\scripts\server-admin.ps1 settings --interactive
.\scripts\server-admin.ps1 profiles list
.\scripts\server-admin.ps1 profiles save office-cuda --note "사내 GPU 기본값"
.\scripts\server-admin.ps1 profiles apply office-cuda
```

### `live-audio.ps1`

마이크 또는 시스템 오디오를 서버 WebSocket으로 스트리밍합니다.

```powershell
.\scripts\live-audio.ps1 -Source system_audio
```

### `audio-e2e.ps1`

WAV 파일 기반 오디오 WebSocket 경로를 확인합니다.

```powershell
.\scripts\audio-e2e.ps1 -WavPath .\artifacts\sample.wav
```

### `send-text.ps1`

텍스트 WebSocket으로 테스트 메시지를 보냅니다.

```powershell
.\scripts\send-text.ps1 session-123 hello meeting start
```

## 공통 규칙

- 루트 `scripts/`는 공식 진입점입니다.
- 같은 역할의 중복 구현은 루트 `scripts/`에 두지 않습니다.
- 공통 콘솔 인코딩 처리는 `common/_console_utf8.ps1`만 사용합니다.
- 서버 전용 Python/PowerShell 도구는 `server/scripts/`에 둡니다.

## `server/scripts`와의 관계

루트 `scripts/`는 입구이고, 실제 서버 지원 도구는 [`server/scripts`](../server/scripts/README.md)에 있습니다.

- `.\scripts\server-admin.ps1` -> `server/scripts/admin/setup_server.py`
- `.\scripts\live-audio.ps1` -> `server/scripts/audio/stream_live_audio_ws.ps1`
- `.\scripts\audio-e2e.ps1` -> `server/scripts/audio/run_audio_ws_e2e.ps1`
- `.\scripts\send-text.ps1` -> `server/scripts/audio/send_text_chunk.py`

즉, 루트는 실행 입구이고 `server/scripts/`는 서버 내부 본체입니다.
