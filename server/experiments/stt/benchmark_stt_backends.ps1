# STT 실험에서 benchmark stt backends 검증 흐름을 수행한다.
param(
    [string]$Dataset,
    [string]$Wav,
    [string]$Name = "single-sample",
    [string]$ReferenceText,
    [ValidateSet("mic", "system_audio", "file")]
    [string]$Source = "system_audio",
    [string[]]$Backend,
    [string[]]$BackendModel,
    [int]$ChunkMs = 250,
    [switch]$Warmup,
    [string]$OutputJson
)

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$pythonExe = Join-Path $projectRoot "venv\\Scripts\\python.exe"
$scriptPath = Join-Path $projectRoot "server\\\experiments\\stt\\benchmark_stt_backends.py"

$argsList = @($scriptPath, "--chunk-ms", $ChunkMs, "--source", $Source, "--name", $Name)

if ($Dataset) { $argsList += @("--dataset", $Dataset) }
if ($Wav) { $argsList += @("--wav", $Wav) }
if ($ReferenceText) { $argsList += @("--reference-text", $ReferenceText) }
if ($Warmup) { $argsList += "--warmup" }
if ($OutputJson) { $argsList += @("--output-json", $OutputJson) }
if ($Backend) {
    foreach ($item in $Backend) {
        $argsList += @("--backend", $item)
    }
}
if ($BackendModel) {
    foreach ($item in $BackendModel) {
        $argsList += @("--backend-model", $item)
    }
}

& $pythonExe @argsList

