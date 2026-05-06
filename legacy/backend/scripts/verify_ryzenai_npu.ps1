param(
    [string]$PythonExe = "",
    [string]$RyzenAIPath = "C:\Program Files\RyzenAI\1.6.1"
)

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
if (-not $PythonExe) {
    $PythonExe = Join-Path $projectRoot "venv\Scripts\python.exe"
}

$env:RYZEN_AI_INSTALLATION_PATH = $RyzenAIPath

Write-Host "Ryzen AI provider 상태를 확인합니다."
& $PythonExe -c "import onnxruntime as ort; print('providers=', ort.get_available_providers())"

Write-Host ""
Write-Host "AMD quicktest를 실행합니다."
& $PythonExe "$RyzenAIPath\quicktest\quicktest.py"
