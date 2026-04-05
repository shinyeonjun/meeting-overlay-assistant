param(
    [ValidateSet("overlay", "web")]
    [string]$Target = "overlay",
    [switch]$BuildOnly
)

$scriptsRoot = $PSScriptRoot
$scriptsParent = Split-Path -Parent $scriptsRoot
$root = Split-Path -Parent $scriptsParent
. (Join-Path $scriptsParent "common\_console_utf8.ps1")
$Host.UI.RawUI.WindowTitle = "CAPS client $Target"
$clientDir = Join-Path $root "client\$Target"

if (-not (Test-Path $clientDir)) {
    Write-Error "클라이언트 디렉터리를 찾을 수 없습니다: $clientDir"
    exit 1
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "npm 실행 파일을 찾을 수 없습니다. Node.js 설치를 확인해 주세요."
    exit 1
}

$command = switch ($Target) {
    "overlay" {
        if ($BuildOnly) { "overlay:build" } else { "overlay:tauri:dev" }
        break
    }
    "web" {
        if ($BuildOnly) { "web:build" } else { "web:dev" }
        break
    }
}

Write-Host ""
Write-Host "CAPS 클라이언트 실행" -ForegroundColor Cyan
Write-Host "  대상:     $Target"
Write-Host "  루트:     $clientDir"
Write-Host "  명령:     npm run $command"
Write-Host "  API URL:  .env.example 기준 overlay=8011 / web=8011"
Write-Host ""

Set-Location $clientDir
npm run $command
