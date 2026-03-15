param(
    [string]$VenvPath = "D:\caps\venv"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$requirementsApp = Join-Path $projectRoot "requirements-app.txt"
$requirementsDev = Join-Path $projectRoot "requirements-dev.txt"

Write-Host "메인 venv를 다시 구성합니다." -ForegroundColor Cyan
Write-Host "  대상 경로: $VenvPath"

if (Test-Path $VenvPath) {
    Write-Host "기존 venv를 삭제합니다." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $VenvPath
}

python -m venv $VenvPath

$pythonExe = Join-Path $VenvPath "Scripts\python.exe"

& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r $requirementsApp
& $pythonExe -m pip install -r $requirementsDev

Write-Host ""
Write-Host "기본 의존성 설치가 끝났습니다." -ForegroundColor Green
Write-Host "RyzenAI 런타임까지 포함하려면 아래 명령을 이어서 실행하세요."
Write-Host "powershell -ExecutionPolicy Bypass -File $projectRoot\server\scripts\env\install_ryzenai_runtime.ps1 -PythonExe $pythonExe"
