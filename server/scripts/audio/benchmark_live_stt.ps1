param(
    [Parameter(Mandatory = $true)]
    [string]$WavPath,
    [string]$Source = "system_audio",
    [string]$ControlBaseUrl = "http://127.0.0.1:8011",
    [string]$LiveBaseUrl = "http://127.0.0.1:8012",
    [int]$ChunkMs = 250,
    [int]$DelayMs = 250,
    [int]$AppendSilenceMs = 2500,
    [int]$PostStreamWaitMs = 4000,
    [int]$SettleTimeoutMs = 20000,
    [int]$SettlePollMs = 1000,
    [int]$StableRounds = 3,
    [int]$MaxAudioMs = 0,
    [string]$Title = "STT 벤치마크",
    [ValidateSet("text", "json")]
    [string]$Output = "text"
)

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
. (Join-Path $projectRoot "scripts\common\_console_utf8.ps1")
$pythonExe = Join-Path $projectRoot "venv\Scripts\python.exe"
$scriptPath = Join-Path $projectRoot "server\scripts\audio\benchmark_live_stt.py"

& $pythonExe `
    $scriptPath `
    --wav $WavPath `
    --source $Source `
    --control-base-url $ControlBaseUrl `
    --live-base-url $LiveBaseUrl `
    --chunk-ms $ChunkMs `
    --delay-ms $DelayMs `
    --append-silence-ms $AppendSilenceMs `
    --post-stream-wait-ms $PostStreamWaitMs `
    --settle-timeout-ms $SettleTimeoutMs `
    --settle-poll-ms $SettlePollMs `
    --stable-rounds $StableRounds `
    --max-audio-ms $MaxAudioMs `
    --title $Title `
    --output $Output
