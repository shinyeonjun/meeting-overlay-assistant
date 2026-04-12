param(
    [switch]$BuildOnly
)

$scriptsRoot = $PSScriptRoot
$root = Split-Path -Parent $scriptsRoot
. (Join-Path $scriptsRoot "common\_console_utf8.ps1")
$clientDir = Join-Path $root "client\overlay"

if (-not (Test-Path $clientDir)) {
    Write-Error "클라이언트 디렉터리를 찾을 수 없습니다: $clientDir"
    exit 1
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "npm 실행 파일을 찾을 수 없습니다. Node.js 설치를 확인해 주세요."
    exit 1
}

$command = if ($BuildOnly) { "overlay:build" } else { "overlay:tauri:dev" }

Write-Host ""
Write-Host "CAPS 클라이언트 실행" -ForegroundColor Cyan
Write-Host "  루트:     $clientDir"
Write-Host "  명령:     npm run $command"
Write-Host "  API URL:  기본값은 client/overlay/.env.example 기준 8011"
Write-Host ""

Set-Location $clientDir
npm run $command
