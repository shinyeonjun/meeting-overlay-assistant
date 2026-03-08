param(
    [Parameter(Mandatory = $true)]
    [string]$Wav,

    [Parameter(Mandatory = $true)]
    [string]$SherpaModelPath,

    [string]$SenseVoiceModelPath = "",

    [string]$ReferenceFile = "",
    [ValidateSet("mic", "system_audio", "file")]
    [string]$Source = "system_audio",
    [int]$ChunkMs = 120,
    [switch]$Warmup,
    [string]$OutputJson = "",
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$benchmarkScript = Join-Path $PSScriptRoot "benchmark_realtime_stt.py"

if (-not $PythonExe) {
    $PythonExe = Join-Path $repoRoot "venv\Scripts\python.exe"
}

$resolvedWav = (Resolve-Path $Wav).Path
$resolvedSherpaModel = (Resolve-Path $SherpaModelPath).Path

$argsList = @(
    $benchmarkScript,
    "--wav", $resolvedWav,
    "--source", $Source,
    "--chunk-ms", $ChunkMs.ToString(),
    "--backend", "faster_whisper_streaming",
    "--backend", "sherpa_onnx_streaming",
    "--backend-model", "sherpa_onnx_streaming=$resolvedSherpaModel",
    "--backend-python", "sherpa_onnx_streaming=$PythonExe"
)

if ($SenseVoiceModelPath) {
    $resolvedSenseVoiceModel = (Resolve-Path $SenseVoiceModelPath).Path
    $argsList += @(
        "--backend", "sensevoice_small_streaming@cpu",
        "--backend-model", "sensevoice_small_streaming@cpu=$resolvedSenseVoiceModel",
        "--backend-python", "sensevoice_small_streaming@cpu=$PythonExe",
        "--backend-arg", "sensevoice_small_streaming@cpu=--device",
        "--backend-arg", "sensevoice_small_streaming@cpu=cpu",
        "--backend", "sensevoice_small_streaming@cuda",
        "--backend-model", "sensevoice_small_streaming@cuda=$resolvedSenseVoiceModel",
        "--backend-python", "sensevoice_small_streaming@cuda=$PythonExe",
        "--backend-arg", "sensevoice_small_streaming@cuda=--device",
        "--backend-arg", "sensevoice_small_streaming@cuda=cuda:0"
    )
}

if ($ReferenceFile) {
    $argsList += @("--reference-file", (Resolve-Path $ReferenceFile).Path)
}

if ($Warmup.IsPresent) {
    $argsList += "--warmup"
}

if ($OutputJson) {
    $argsList += @("--output-json", $OutputJson)
}

Write-Host "[compare-streaming] python=$PythonExe"
Write-Host "[compare-streaming] wav=$resolvedWav"
Write-Host "[compare-streaming] source=$Source"
Write-Host "[compare-streaming] sherpa_model=$resolvedSherpaModel"
if ($SenseVoiceModelPath) {
    Write-Host "[compare-streaming] sensevoice_model=$resolvedSenseVoiceModel"
}

& $PythonExe @argsList
