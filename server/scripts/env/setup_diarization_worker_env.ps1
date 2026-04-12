param(
    [string]$VenvPath = "D:\caps\venvs\diarization"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$requirementsPath = Join-Path $projectRoot "requirements-diarization-worker.txt"
$workerScriptPath = "server/scripts/workers/pyannote_worker.py"

Write-Host "diarization worker 전용 venv를 구성합니다." -ForegroundColor Cyan
Write-Host "  대상 경로: $VenvPath"

if (-not (Test-Path $VenvPath)) {
    python -m venv $VenvPath
}

$pythonExe = Join-Path $VenvPath "Scripts\python.exe"

& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r $requirementsPath

Write-Host ""
Write-Host "설치가 완료되었습니다." -ForegroundColor Green
Write-Host ".env에 아래 값을 설정하세요."
Write-Host "SPEAKER_DIARIZER_BACKEND=pyannote_worker"
Write-Host "SPEAKER_DIARIZER_WORKER_PYTHON=$pythonExe"
Write-Host "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH=$workerScriptPath"
Write-Host "SPEAKER_DIARIZER_DEVICE=cpu"
