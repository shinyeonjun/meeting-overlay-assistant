param(
    [switch]$Once,
    [int]$BatchSize = 5,
    [int]$LeaseSeconds = 120,
    [double]$QueueBlockSeconds = 0,
    [string]$WorkerId = "",
    [double]$PollIntervalSeconds = 0
)

$scriptsRoot = $PSScriptRoot
$scriptsParent = Split-Path -Parent $scriptsRoot
$root = Split-Path -Parent $scriptsParent
. (Join-Path $scriptsParent "common\_console_utf8.ps1")
$envPath = Join-Path $root ".env"
$pythonExe = Get-CapsPythonExe -Root $root

$resolvedQueueBlockSeconds = Resolve-CapsWorkerNumber -Value $QueueBlockSeconds -EnvPath $envPath -Key "NOTE_CORRECTION_JOB_QUEUE_BLOCK_SECONDS" -DefaultValue "15"
$resolvedPollIntervalSeconds = Resolve-CapsWorkerNumber -Value $PollIntervalSeconds -EnvPath $envPath -Key "NOTE_CORRECTION_JOB_FALLBACK_POLL_SECONDS" -DefaultValue "30"

if (-not (Test-Path $pythonExe)) {
    Write-Error "가상환경 Python을 찾을 수 없습니다: $pythonExe"
    exit 1
}

$moduleArguments = @(
    "--batch-size", "$BatchSize",
    "--lease-seconds", "$LeaseSeconds",
    "--queue-block-seconds", "$resolvedQueueBlockSeconds",
    "--poll-interval-seconds", "$resolvedPollIntervalSeconds"
)

if ($Once) {
    $moduleArguments += "--once"
}

if ($WorkerId) {
    $moduleArguments += @("--worker-id", $WorkerId)
}

$workerIdLabel = if ($WorkerId) { $WorkerId } else { '<auto>' }

Invoke-CapsPythonWorker `
    -PythonExe $pythonExe `
    -Root $root `
    -WindowTitle "CAPS note correction worker" `
    -Module 'server.app.workers.report.note_correction_worker' `
    -ModuleArguments $moduleArguments `
    -Banner "CAPS note correction worker 시작" `
    -BannerRows @(
        @('루트:', $root),
        @('batch size:', "$BatchSize"),
        @('lease:', "$LeaseSeconds"),
        @('queue wait:', "$resolvedQueueBlockSeconds"),
        @('poll:', "$resolvedPollIntervalSeconds"),
        @('worker id:', $workerIdLabel),
        @('once:', "$Once")
    )
