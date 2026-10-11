$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
Set-Location $projectRoot

# 저장소 가상환경을 우선 쓴다. 없으면 PATH의 python으로 떨어진다.
$pythonExe = Join-Path $projectRoot "venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Warning "venv가 없어 PATH의 python을 씁니다: $pythonExe"
    $pythonExe = "python"
}

& $pythonExe -m pytest -v
exit $LASTEXITCODE
