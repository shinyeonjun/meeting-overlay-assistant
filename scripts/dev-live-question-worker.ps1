param(
    [switch]$Once,
    [string]$ConsumerName = "",
    [double]$BlockSeconds = 0
)

$scriptsRoot = $PSScriptRoot
$root = Split-Path -Parent $scriptsRoot
. (Join-Path $scriptsRoot "common\_console_utf8.ps1")
$Host.UI.RawUI.WindowTitle = "CAPS live question worker"
$pythonExe = Join-Path $root "venv\Scripts\python.exe"
$envPath = Join-Path $root ".env"

$resolvedBlockSeconds = if ($BlockSeconds -gt 0) {
    $BlockSeconds
} else {
    [double](Get-DotEnvValue -EnvPath $envPath -Key "LIVE_QUESTION_STREAM_BLOCK_SECONDS" -DefaultValue "5")
}

if (-not (Test-Path $pythonExe)) {
    Write-Error "가상환경 Python을 찾을 수 없습니다: $pythonExe"
    exit 1
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
Write-Host "CAPS live question worker 시작" -ForegroundColor Cyan
Write-Host "  루트:        $root"
Write-Host "  queue wait:  $resolvedBlockSeconds"
Write-Host "  consumer:    $(if ($ConsumerName) { $ConsumerName } else { '<auto>' })"
Write-Host "  once:        $Once"
Write-Host ""

Set-Location $root
& $pythonExe @arguments
