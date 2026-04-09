param(
    [string]$Manifest = "D:\stt_data\fine_tuning\eval_sets\public_baseline\ksponspeech_eval_quick200.jsonl",
    [int]$Limit = 5,
    [ValidateSet("mic", "system_audio", "file")]
    [string]$Source = "system_audio",
    [int]$ChunkMs = 120,
    [switch]$Warmup,
    [string]$SherpaModelPath = "D:\caps\server\models\stt\sherpa-onnx-streaming-zipformer-korean-2024-06-16",
    [string]$SenseVoiceModelPath = "D:\caps\server\models\stt\SenseVoiceSmall",
    [switch]$NoSenseVoice,
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonExe = Join-Path $repoRoot "venv\Scripts\python.exe"
$scriptPath = Join-Path $repoRoot "server\experiments\stt\compare_streaming_manifest.py"

$argsList = @(
    $scriptPath,
    "--manifest", (Resolve-Path $Manifest).Path,
    "--limit", $Limit.ToString(),
    "--source", $Source,
    "--chunk-ms", $ChunkMs.ToString(),
    "--sherpa-model-path", (Resolve-Path $SherpaModelPath).Path,
    "--python-exe", $pythonExe
)

if (-not $NoSenseVoice.IsPresent -and $SenseVoiceModelPath) {
    $argsList += @("--sensevoice-model-path", (Resolve-Path $SenseVoiceModelPath).Path)
}

if ($Warmup.IsPresent) {
    $argsList += "--warmup"
}

if ($OutputDir) {
    $resolvedOutputDir = (Resolve-Path -LiteralPath $OutputDir -ErrorAction SilentlyContinue)
    if (-not $resolvedOutputDir) {
        New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
        $resolvedOutputDir = Resolve-Path -LiteralPath $OutputDir
    }
    $argsList += @("--output-dir", $resolvedOutputDir.Path)
}

Write-Host "[live-batch] python=$pythonExe"
Write-Host "[live-batch] manifest=$Manifest"
Write-Host "[live-batch] limit=$Limit source=$Source chunk_ms=$ChunkMs"
Write-Host "[live-batch] sherpa_model=$SherpaModelPath"
if (-not $NoSenseVoice.IsPresent -and $SenseVoiceModelPath) {
    Write-Host "[live-batch] sensevoice_model=$SenseVoiceModelPath"
}
if ($OutputDir) {
    Write-Host "[live-batch] output_dir=$($resolvedOutputDir.Path)"
}

& $pythonExe @argsList
