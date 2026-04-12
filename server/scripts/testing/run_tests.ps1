# run tests 모듈을 설명한다.
íë¤.
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
Set-Location $projectRoot
python -m pytest -v
