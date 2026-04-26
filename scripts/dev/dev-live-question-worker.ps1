param(
    [switch]$Once,
    [string]$ConsumerName = "",
    [double]$BlockSeconds = 0
)

$scriptsRoot = $PSScriptRoot
$scriptsParent = Split-Path -Parent $scriptsRoot
$root = Split-Path -Parent $scriptsParent
. (Join-Path $scriptsParent "common\_console_utf8.ps1")
$Host.UI.RawUI.WindowTitle = "CAPS live question worker"
$pythonExe = Join-Path $root "venv\Scripts\python.exe"
$envPath = Join-Path $root ".env"
$liveQuestionAnalysisEnabled = (Get-DotEnvValue -EnvPath $envPath -Key "LIVE_QUESTION_ANALYSIS_ENABLED" -DefaultValue "false").Trim().ToLowerInvariant()
$enabledTokens = @("1", "true", "yes", "on")

$resolvedBlockSeconds = if ($BlockSeconds -gt 0) {
    $BlockSeconds
} else {
    [double](Get-DotEnvValue -EnvPath $envPath -Key "LIVE_QUESTION_STREAM_BLOCK_SECONDS" -DefaultValue "5")
}

if (-not (Test-Path $pythonExe)) {
    Write-Error "Python venv not found: $pythonExe"
    exit 1
}

if (-not ($enabledTokens -contains $liveQuestionAnalysisEnabled)) {
    Write-Host ""
    Write-Host "LIVE_QUESTION_ANALYSIS_ENABLED=false 이므로 live question worker를 시작하지 않습니다." -ForegroundColor Yellow
    exit 0
}

$arguments = @(
    "-m",
    "server.app.workers.live_question_worker",
    "--block-seconds", "$resolvedBlockSeconds"
)

if ($Once) {
    $arguments += "--once"
}

if ($ConsumerName) {
    $arguments += @("--consumer-name", $ConsumerName)
}

Write-Host ""
Write-Host "CAPS live question worker start" -ForegroundColor Cyan
Write-Host "  root:       $root"
Write-Host "  queue wait: $resolvedBlockSeconds"
Write-Host "  consumer:   $(if ($ConsumerName) { $ConsumerName } else { '<auto>' })"
Write-Host "  once:       $Once"
Write-Host ""

Set-Location $root
& $pythonExe @arguments
