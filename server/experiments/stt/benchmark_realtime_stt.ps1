param(
    [Parameter(Mandatory = $true)]
    [string]$Wav,
    [string]$ReferenceFile,
    [string]$Source = "system_audio",
    [string[]]$Backend = @(),
    [string[]]$BackendModel = @(),
    [int]$ChunkMs = 120,
    [switch]$Warmup,
    [string]$OutputJson
)

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$pythonExe = Join-Path $projectRoot "venv\\Scripts\\python.exe"
$scriptPath = Join-Path $projectRoot "server\\\experiments\\stt\\benchmark_realtime_stt.py"

$argsList = @($scriptPath, "--wav", $Wav, "--source", $Source, "--chunk-ms", $ChunkMs)
if ($ReferenceFile) {
    $argsList += @("--reference-file", $ReferenceFile)
}
foreach ($backendName in $Backend) {
    $argsList += @("--backend", $backendName)
}
foreach ($backendModel in $BackendModel) {
    $argsList += @("--backend-model", $backendModel)
}
if ($Warmup) {
    $argsList += "--warmup"
}
if ($OutputJson) {
    $argsList += @("--output-json", $OutputJson)
}

& $pythonExe @argsList

