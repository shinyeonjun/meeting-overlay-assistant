param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$scriptsRoot = $PSScriptRoot
$root = Split-Path -Parent $scriptsRoot
. (Join-Path $scriptsRoot "common\_console_utf8.ps1")
$scriptPath = Join-Path $root "server\scripts\audio\run_audio_ws_e2e.ps1"

if (-not (Test-Path $scriptPath)) {
    Write-Error "오디오 E2E 스크립트를 찾을 수 없습니다: $scriptPath"
    exit 1
}

if (-not $Arguments -or $Arguments.Count -eq 0) {
    Write-Host ""
    Write-Host "CAPS 오디오 WebSocket E2E" -ForegroundColor Cyan
    Write-Host "  예시 1: .\scripts\audio-e2e.ps1 -WavPath .\artifacts\sample.wav"
    Write-Host "  예시 2: .\scripts\audio-e2e.ps1 -WavPath .\artifacts\sample.wav -ChunkMs 250 -DelayMs 150"
    Write-Host "  기본 서버: http://127.0.0.1:8011"
    Write-Host ""
    exit 0
}

& $scriptPath @Arguments
