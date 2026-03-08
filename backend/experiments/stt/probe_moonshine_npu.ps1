param(
    [Parameter(Mandatory = $true)]
    [string]$ModelPath,
    [string]$Provider = "VitisAIExecutionProvider",
    [string]$RyzenAiInstallationPath,
    [string[]]$InputShape = @(),
    [string]$OutputJson
)

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$pythonExe = Join-Path $projectRoot "venv\\Scripts\\python.exe"
$scriptPath = Join-Path $projectRoot "backend\\experiments\\stt\\probe_moonshine_npu.py"

$argsList = @($scriptPath, "--model-path", $ModelPath, "--provider", $Provider)
if ($RyzenAiInstallationPath) {
    $argsList += @("--ryzen-ai-installation-path", $RyzenAiInstallationPath)
}
foreach ($shape in $InputShape) {
    $argsList += @("--input-shape", $shape)
}
if ($OutputJson) {
    $argsList += @("--output-json", $OutputJson)
}

& $pythonExe @argsList
