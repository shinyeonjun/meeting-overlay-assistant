# 운영 보조 스크립트에서 live audio 작업을 수행한다.
ì ìííë¤.
﻿param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$scriptsRoot = $PSScriptRoot
$scriptsParent = Split-Path -Parent $scriptsRoot
$root = Split-Path -Parent $scriptsParent
. (Join-Path $scriptsParent "common\_console_utf8.ps1")
$scriptPath = Join-Path $root "server\scripts\audio\stream_live_audio_ws.ps1"

if (-not (Test-Path $scriptPath)) {
    Write-Error "라이브 오디오 스크립트를 찾을 수 없습니다: $scriptPath"
    exit 1
}

if (-not $Arguments -or $Arguments.Count -eq 0) {
    Write-Host ""
    Write-Host "CAPS 라이브 오디오 브리지" -ForegroundColor Cyan
    Write-Host "  예시 1: .\scripts\live-audio.ps1 -Source system_audio"
    Write-Host "  예시 2: .\scripts\live-audio.ps1 -Source mic -DeviceName ""USB Microphone"""
    Write-Host "  기본 서버: http://127.0.0.1:8011"
    Write-Host ""
    exit 0
}

& $scriptPath @Arguments
