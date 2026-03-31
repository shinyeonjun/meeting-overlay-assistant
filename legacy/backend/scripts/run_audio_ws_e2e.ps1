param(
    [Parameter(Mandatory = $true)]
    [string]$WavPath,
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [int]$ChunkMs = 1000,
    [int]$DelayMs = 150,
    [string]$Title = "오디오 E2E 테스트"
)

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$pythonExe = Join-Path $projectRoot "venv\\Scripts\\python.exe"
$scriptPath = Join-Path $projectRoot "backend\\scripts\\run_audio_ws_e2e.py"

& $pythonExe $scriptPath --wav $WavPath --base-url $BaseUrl --chunk-ms $ChunkMs --delay-ms $DelayMs --title $Title
