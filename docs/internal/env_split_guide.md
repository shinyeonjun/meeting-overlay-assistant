# 환경 분리 재설치 가이드

## 목적

이 프로젝트는 이제 두 개의 Python 환경으로 나누는 것이 기준이다.

1. 메인 앱 환경
- FastAPI
- faster-whisper
- RyzenAI / ONNX Runtime
- 오버레이 UI, 실시간 STT, 이벤트 분석

2. diarization worker 환경
- pyannote.audio
- 별도 torch / numpy 스택
- 회의 후 화자 분리

이렇게 나누는 이유는 `pyannote.audio`와 메인 앱의 `numpy / torch / onnxruntime / RyzenAI` 조합이 한 환경에서 충돌하기 때문이다.

## 메인 앱 venv 재설치

```powershell
cd D:\caps
powershell -ExecutionPolicy Bypass -File .\backend\scripts\rebuild_main_env.ps1
```

RyzenAI 런타임까지 다시 붙이려면:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\install_ryzenai_runtime.ps1 -PythonExe D:\caps\venv\Scripts\python.exe
```

## diarization worker venv 설치

```powershell
cd D:\caps
powershell -ExecutionPolicy Bypass -File .\backend\scripts\setup_diarization_worker_env.ps1
```

기본 경로는 아래처럼 잡힌다.

```text
D:\caps\venvs\diarization\Scripts\python.exe
```

## `.env` 연결 예시

메인 앱은 기본값으로 안전하게 `unknown_speaker`를 쓴다.

worker를 실제로 연결할 때만 아래처럼 바꾼다.

```env
SPEAKER_DIARIZER_BACKEND=pyannote_worker
SPEAKER_DIARIZER_WORKER_PYTHON=D:\caps\venvs\diarization\Scripts\python.exe
SPEAKER_DIARIZER_WORKER_SCRIPT_PATH=backend/scripts/pyannote_worker.py
SPEAKER_DIARIZER_DEVICE=cpu
```

## 주의사항

- 실시간 STT 주력은 현재 `faster-whisper + GPU`다.
- `pyannote`는 회의 후 후처리 경로로 보는 것이 맞다.
- `RTX 5070`에서 `pyannote` GPU는 현재 torch wheel 호환성 이슈가 있어, 우선 `cpu`로 붙이는 것을 권장한다.

## 서버 재시작

```powershell
cd D:\caps
uvicorn backend.app.main:app --reload
```

## 확인 방법

세션 생성 후 `audio_path`를 붙여 리포트를 만들면 된다.

```powershell
$session = Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/sessions -Method Post -ContentType "application/json" -Body '{"title":"worker test","mode":"meeting","source":"file"}'

$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/reports/$($session.id)/markdown?audio_path=D:\caps\tests\video\test_16k_mono_15s.wav" -Method Post

Get-Content $response.file_path
```
