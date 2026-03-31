param(
    [string]$VenvPath = "D:\caps\venv"
)

$ErrorActionPreference = "Stop"

Write-Host "메인 앱 venv를 재구성합니다."
Write-Host "대상 경로: $VenvPath"

if (Test-Path $VenvPath) {
    Write-Host "기존 venv를 삭제합니다."
    Remove-Item -Recurse -Force $VenvPath
}

python -m venv $VenvPath

$pythonExe = Join-Path $VenvPath "Scripts\python.exe"

& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r D:\caps\requirements-app.txt
& $pythonExe -m pip install -r D:\caps\requirements-dev.txt

Write-Host "RyzenAI 런타임 설치가 필요하면 아래 스크립트를 추가로 실행하세요."
Write-Host "powershell -ExecutionPolicy Bypass -File D:\caps\legacy\backend\scripts\install_ryzenai_runtime.ps1 -PythonExe $pythonExe"
