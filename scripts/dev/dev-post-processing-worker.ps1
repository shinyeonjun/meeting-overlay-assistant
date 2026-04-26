param(
    [switch]$Once,
    [int]$BatchSize = 1,
    [int]$LeaseSeconds = 300,
    [double]$QueueBlockSeconds = 0,
    [string]$WorkerId = "",
    [double]$PollIntervalSeconds = 0
)

$scriptsRoot = $PSScriptRoot
$scriptsParent = Split-Path -Parent $scriptsRoot
$root = Split-Path -Parent $scriptsParent
. (Join-Path $scriptsParent "common\\_console_utf8.ps1")
$Host.UI.RawUI.WindowTitle = "CAPS post-processing worker"
$pythonExe = Join-Path $root "venv\\Scripts\\python.exe"
$envPath = Join-Path $root ".env"

$resolvedQueueBlockSeconds = if ($QueueBlockSeconds -gt 0) {
    $QueueBlockSeconds
} else {
    [double](Get-DotEnvValue -EnvPath $envPath -Key "SESSION_POST_PROCESSING_JOB_QUEUE_BLOCK_SECONDS" -DefaultValue "15")
}

$resolvedPollIntervalSeconds = if ($PollIntervalSeconds -gt 0) {
    $PollIntervalSeconds
} else {
    [double](Get-DotEnvValue -EnvPath $envPath -Key "SESSION_POST_PROCESSING_JOB_FALLBACK_POLL_SECONDS" -DefaultValue "30")
}

if (-not (Test-Path $pythonExe)) {
    Write-Error "가상환경 Python을 찾을 수 없습니다: $pythonExe"
    exit 1
}

$arguments = @(
    '-m',
    'server.app.workers.session_post_processing_worker',
    '--batch-size', "$BatchSize",
    '--lease-seconds', "$LeaseSeconds",
    '--queue-block-seconds', "$resolvedQueueBlockSeconds",
    '--poll-interval-seconds', "$resolvedPollIntervalSeconds"
)

if ($Once) {
    $arguments += '--once'
}

if ($WorkerId) {
    $arguments += @('--worker-id', $WorkerId)
}

Write-Host ""
Write-Host "CAPS post-processing worker 시작" -ForegroundColor Cyan
Write-Host "  루트:       $root"
Write-Host "  batch size: $BatchSize"
Write-Host "  lease:      $LeaseSeconds"
Write-Host "  queue wait: $resolvedQueueBlockSeconds"
Write-Host "  poll:       $resolvedPollIntervalSeconds"
Write-Host "  worker id:  $(if ($WorkerId) { $WorkerId } else { '<auto>' })"
Write-Host "  once:       $Once"
Write-Host ""

Set-Location $root
& $pythonExe @arguments
