param(
    [switch]$Once,
    [string]$ConsumerName = "",
    [double]$BlockSeconds = 0
)

$scriptsRoot = $PSScriptRoot
$scriptsParent = Split-Path -Parent $scriptsRoot
$root = Split-Path -Parent $scriptsParent
. (Join-Path $scriptsParent "common\_console_utf8.ps1")
$envPath = Join-Path $root ".env"
$pythonExe = Get-CapsPythonExe -Root $root

$resolvedBlockSeconds = Resolve-CapsWorkerNumber -Value $BlockSeconds -EnvPath $envPath -Key "LIVE_QUESTION_STREAM_BLOCK_SECONDS" -DefaultValue "5"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Python venv not found: $pythonExe"
    exit 1
}

$moduleArguments = @(
    "--block-seconds", "$resolvedBlockSeconds"
)

if ($Once) {
    $moduleArguments += "--once"
}

if ($ConsumerName) {
    $moduleArguments += @("--consumer-name", $ConsumerName)
}

$consumerLabel = if ($ConsumerName) { $ConsumerName } else { '<auto>' }

Invoke-CapsPythonWorker `
    -PythonExe $pythonExe `
    -Root $root `
    -WindowTitle "CAPS live question worker" `
    -Module 'server.app.workers.live_question_worker' `
    -ModuleArguments $moduleArguments `
    -Banner "CAPS live question worker start" `
    -BannerRows @(
        @('root:', $root),
        @('queue wait:', "$resolvedBlockSeconds"),
        @('consumer:', $consumerLabel),
        @('once:', "$Once")
    )
