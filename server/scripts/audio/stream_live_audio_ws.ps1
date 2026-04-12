# 오디오 운영 스크립트에서 stream live audio ws 작업을 수행한다.
ì ìííë¤.
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("mic", "system_audio")]
    [string]$Source,
    [string]$BaseUrl = "http://127.0.0.1:8011",
    [string]$Title = "live-audio-test",
    [string]$DeviceName = "",
    [int]$SampleRate = 16000,
    [int]$Channels = 1,
    [int]$ChunkMs = 250,
    [int]$MaxChunks = 0,
    [switch]$ListDevices
)

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
. (Join-Path $projectRoot "scripts\common\_console_utf8.ps1")
$pythonExe = Join-Path $projectRoot "venv\Scripts\python.exe"
$scriptPath = Join-Path $projectRoot "server\scripts\audio\stream_live_audio_ws.py"

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
