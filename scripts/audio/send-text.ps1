# 운영 보조 스크립트에서 send text 작업을 수행한다.
ì ìííë¤.
﻿param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$scriptsRoot = $PSScriptRoot
$scriptsParent = Split-Path -Parent $scriptsRoot
$root = Split-Path -Parent $scriptsParent
. (Join-Path $scriptsParent "common\_console_utf8.ps1")
$pythonExe = Join-Path $root "venv\Scripts\python.exe"
$scriptPath = Join-Path $root "server\scripts\audio\send_text_chunk.py"

if (-not (Test-Path $pythonExe)) {
    Write-Error "가상환경 Python을 찾을 수 없습니다: $pythonExe"
    exit 1
}

if (-not (Test-Path $scriptPath)) {
    Write-Error "텍스트 전송 스크립트를 찾을 수 없습니다: $scriptPath"
    exit 1
}

if (-not $Arguments -or $Arguments.Count -eq 0) {
    Write-Host ""
    Write-Host "CAPS 텍스트 WebSocket 전송" -ForegroundColor Cyan
    Write-Host "  예시 1: .\scripts\send-text.ps1 session-123 hello meeting start"
    Write-Host "  예시 2: .\scripts\send-text.ps1 session-123 test message --base-url http://127.0.0.1:8011"
    Write-Host ""
    & $pythonExe $scriptPath --help
    exit $LASTEXITCODE
}

Set-Location $root
& $pythonExe $scriptPath @Arguments
