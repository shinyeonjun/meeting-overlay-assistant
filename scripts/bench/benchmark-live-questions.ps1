# 운영 보조 스크립트에서 benchmark live questions 작업을 수행한다.
ì ìííë¤.
param(
    [string]$Dataset = "",
    [string]$Backend = "",
    [string]$Model = "",
    [string]$BaseUrl = "",
    [string]$ApiKey = "",
    [double]$TimeoutSeconds = 0,
    [int]$Limit = 0,
    [ValidateSet("text", "json")]
    [string]$Output = "text",
    [string]$SaveJson = ""
)

$scriptsRoot = $PSScriptRoot
$scriptsParent = Split-Path -Parent $scriptsRoot
$root = Split-Path -Parent $scriptsParent
. (Join-Path $scriptsParent "common\_console_utf8.ps1")
$Host.UI.RawUI.WindowTitle = "CAPS live question benchmark"
$pythonExe = Join-Path $root "venv\Scripts\python.exe"
$scriptPath = Join-Path $root "server\scripts\audio\benchmark_live_questions.py"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Python venv not found: $pythonExe"
    exit 1
}

if (-not (Test-Path $scriptPath)) {
    Write-Error "Benchmark script not found: $scriptPath"
    exit 1
}

$arguments = @($scriptPath, "--output", $Output)

if ($Dataset) {
    $arguments += @("--dataset", $Dataset)
}

if ($Backend) {
    $arguments += @("--backend", $Backend)
}

if ($Model) {
    $arguments += @("--model", $Model)
}

if ($BaseUrl) {
    $arguments += @("--base-url", $BaseUrl)
}

if ($ApiKey) {
    $arguments += @("--api-key", $ApiKey)
}

if ($TimeoutSeconds -gt 0) {
    $arguments += @("--timeout-seconds", "$TimeoutSeconds")
}

if ($Limit -gt 0) {
    $arguments += @("--limit", "$Limit")
}

if ($SaveJson) {
    $arguments += @("--save-json", $SaveJson)
}

Write-Host ""
Write-Host "CAPS live question benchmark start" -ForegroundColor Cyan
Write-Host "  root:      $root"
Write-Host "  dataset:   $(if ($Dataset) { $Dataset } else { '<default>' })"
Write-Host "  backend:   $(if ($Backend) { $Backend } else { '<env default>' })"
Write-Host "  model:     $(if ($Model) { $Model } else { '<env default>' })"
Write-Host "  output:    $Output"
Write-Host "  save_json: $(if ($SaveJson) { $SaveJson } else { '<none>' })"
Write-Host ""

Set-Location $root
& $pythonExe @arguments
