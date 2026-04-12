# 개발 환경 스크립트에서 install ryzenai runtime 작업을 수행한다.
ì ìííë¤.
param(
    [string]$RyzenAIPath = $env:RYZEN_AI_INSTALLATION_PATH,
    [string]$PythonExe = ""
)

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path

if (-not $RyzenAIPath) {
    $RyzenAIPath = "C:\Program Files\RyzenAI\1.6.1"
}

if (-not $PythonExe) {
    $PythonExe = Join-Path $ProjectRoot "venv\Scripts\python.exe"
}

if (-not (Test-Path $RyzenAIPath)) {
    throw "Ryzen AI 설치 경로를 찾지 못했습니다: $RyzenAIPath"
}

$requirementsFile = Join-Path $RyzenAIPath "requirements.txt"
if (-not (Test-Path $requirementsFile)) {
    throw "requirements.txt를 찾지 못했습니다: $requirementsFile"
}

if (-not (Test-Path $PythonExe)) {
    throw "Python 실행 파일을 찾지 못했습니다: $PythonExe"
}

$PythonExe = (Resolve-Path $PythonExe).Path

Write-Host "Ryzen AI 런타임 패키지를 설치합니다."
Write-Host "설치 경로: $RyzenAIPath"
Write-Host "Python 경로: $PythonExe"

$corePackages = @(
    "numpy==1.26.4",
    "device_essentials_strx_overlay-1.6.1-py3-none-any.whl",
    "llvm_aie_lightweight-1.6.1-py3-none-win_amd64.whl",
    "ryzenai_dynamic_dispatch-1.6.1-cp312-cp312-win_amd64.whl",
    "ryzenai_onnx_utils-1.6.1-py3-none-any.whl",
    "vaie_cpplus-1.6.1-py3-none-win_amd64.whl",
    "vaie_overlay-1.6.1-py3-none-win_amd64.whl",
    "voe-1.6.1-py3-none-win_amd64.whl",
    "flexml_lite-1.6.1-py312-none-win_amd64.whl",
    "onnxruntime_vitisai-1.23.2-cp312-cp312-win_amd64.whl",
    "onnxruntime_genai_directml_ryzenai-0.9.2-cp312-cp312-win_amd64.whl"
)

$stalePaths = @(
    "Lib\\site-packages\\onnxruntime",
    "Lib\\site-packages\\onnxruntime-*.dist-info",
    "Lib\\site-packages\\onnxruntime_vitisai-*.dist-info",
    "Lib\\site-packages\\onnxruntime_genai",
    "Lib\\site-packages\\onnxruntime_genai_directml_ryzenai-*.dist-info"
)

Push-Location $RyzenAIPath
try {
    & $PythonExe -m pip uninstall -y onnxruntime onnxruntime-vitisai onnxruntime_extensions onnxruntime-genai onnxruntime-genai-directml-ryzenai | Out-Null

    $pythonRoot = Split-Path (Split-Path $PythonExe -Parent) -Parent
    foreach ($relativePath in $stalePaths) {
        $resolvedPaths = Get-ChildItem -Path (Join-Path $pythonRoot $relativePath) -ErrorAction SilentlyContinue
        foreach ($pathEntry in $resolvedPaths) {
            if (Test-Path $pathEntry.FullName) {
                Remove-Item -Path $pathEntry.FullName -Recurse -Force
            }
        }
    }

    foreach ($entry in $corePackages) {
        if ($entry -like "*.whl") {
            $wheelPath = Join-Path $RyzenAIPath $entry
            if (-not (Test-Path $wheelPath)) {
                throw "필수 wheel을 찾지 못했습니다: $wheelPath"
            }
            & $PythonExe -m pip install --force-reinstall --no-deps $wheelPath
        }
        else {
            & $PythonExe -m pip install --force-reinstall $entry
        }

        if ($LASTEXITCODE -ne 0) {
            throw "패키지 설치에 실패했습니다: $entry"
        }
    }
}
finally {
    Pop-Location
}

Write-Host "Ryzen AI 런타임 패키지 설치가 끝났습니다."
