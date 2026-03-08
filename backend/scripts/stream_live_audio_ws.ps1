param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("mic", "system_audio")]
    [string]$Source,
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$Title = "live-audio-test",
    [string]$DeviceName = "",
    [int]$SampleRate = 16000,
    [int]$Channels = 1,
    [int]$ChunkMs = 250,
    [int]$MaxChunks = 0,
    [switch]$ListDevices
)

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$pythonExe = Join-Path $projectRoot "venv\Scripts\python.exe"
$scriptPath = Join-Path $projectRoot "backend\scripts\stream_live_audio_ws.py"

$argsList = @(
    $scriptPath,
    "--source", $Source,
    "--base-url", $BaseUrl,
    "--title", $Title,
    "--sample-rate", "$SampleRate",
    "--channels", "$Channels",
    "--chunk-ms", "$ChunkMs",
    "--max-chunks", "$MaxChunks"
)

if ($DeviceName) {
    $argsList += @("--device-name", $DeviceName)
}

if ($ListDevices) {
    $argsList += @("--list-devices")
}

& $pythonExe @argsList
