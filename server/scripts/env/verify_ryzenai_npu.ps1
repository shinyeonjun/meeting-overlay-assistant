# 개발 환경 스크립트에서 verify ryzenai npu 작업을 수행한다.
ì ìííë¤.
param(
    [string]$PythonExe = "D:\caps\venv\Scripts\python.exe",
    [string]$RyzenAIPath = "C:\Program Files\RyzenAI\1.6.1"
)

$env:RYZEN_AI_INSTALLATION_PATH = $RyzenAIPath

Write-Host "Ryzen AI provider 상태를 확인합니다."
& $PythonExe -c "import onnxruntime as ort; print('providers=', ort.get_available_providers())"

Write-Host ""
Write-Host "AMD quicktest를 실행합니다."
& $PythonExe "$RyzenAIPath\quicktest\quicktest.py"
