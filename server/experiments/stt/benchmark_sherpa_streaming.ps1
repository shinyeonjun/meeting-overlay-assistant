param(
    [Parameter(Mandatory = $true)]
    [string]$Wav,

    [Parameter(Mandatory = $true)]
    [string]$ModelPath,

    [string]$Name = "sherpa-streaming-sample",
    [ValidateSet("mic", "system_audio", "file")]
    [string]$Source = "system_audio",
    [string]$ReferenceText = "",
    [string]$ReferenceFile = "",
    [int]$ChunkMs = 120,
    [string]$PythonExe = "",
    [switch]$Warmup
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$benchmarkScript = Join-Path $PSScriptRoot "benchmark_realtime_stt.py"

if (-not $PythonExe) {
    $PythonExe = Join-Path $repoRoot "venv\Scripts\python.exe"
}

$arguments = @(
    $benchmarkScript,
    "--wav", (Resolve-Path $Wav).Path,
    "--name", $Name,
    "--source", $Source,
    "--backend", "sherpa_onnx_streaming",
    "--backend-model", "sherpa_onnx_streaming=$((Resolve-Path $ModelPath).Path)",
    "--chunk-ms", $ChunkMs.ToString(),
    "--backend-python", "sherpa_onnx_streaming=$PythonExe"
)

if ($ReferenceText) {
    $arguments += @("--reference-text", $ReferenceText)
}

if ($ReferenceFile) {
    $arguments += @("--reference-file", (Resolve-Path $ReferenceFile).Path)
}

if ($Warmup.IsPresent) {
    $arguments += "--warmup"
}

Write-Host "[sherpa-benchmark] python=$PythonExe"
Write-Host "[sherpa-benchmark] wav=$Wav"
Write-Host "[sherpa-benchmark] model=$ModelPath"
& $PythonExe @arguments
