param(
    [string]$VenvPath = "D:\caps\venvs\diarization"
)

$ErrorActionPreference = "Stop"

Write-Host "diarization worker 전용 venv를 구성합니다."
Write-Host "대상 경로: $VenvPath"

if (-not (Test-Path $VenvPath)) {
    python -m venv $VenvPath
}

$pythonExe = Join-Path $VenvPath "Scripts\python.exe"

& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r D:\caps\requirements-diarization-worker.txt

Write-Host "설치가 끝났습니다."
Write-Host "메인 앱 .env에 아래처럼 연결하세요."
Write-Host "SPEAKER_DIARIZER_BACKEND=pyannote_worker"
Write-Host "SPEAKER_DIARIZER_WORKER_PYTHON=$pythonExe"
Write-Host "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH=backend/scripts/pyannote_worker.py"
Write-Host "SPEAKER_DIARIZER_DEVICE=cpu"
