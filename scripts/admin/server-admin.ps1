param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$scriptsRoot = $PSScriptRoot
$scriptsParent = Split-Path -Parent $scriptsRoot
$root = Split-Path -Parent $scriptsParent
. (Join-Path $scriptsParent "common\_console_utf8.ps1")
$pythonExe = Join-Path $root "venv\Scripts\python.exe"
$scriptPath = Join-Path $root "server\scripts\admin\setup_server.py"

if (-not (Test-Path $pythonExe)) {
    Write-Error "가상환경 Python을 찾을 수 없습니다: $pythonExe"
    exit 1
}

if (-not (Test-Path $scriptPath)) {
    Write-Error "서버 관리 스크립트를 찾을 수 없습니다: $scriptPath"
    exit 1
}

if (-not $Arguments -or $Arguments.Count -eq 0) {
    Write-Host ""
    Write-Host "CAPS 서버 관리 CLI" -ForegroundColor Cyan
    Write-Host "  예시 1: .\scripts\server-admin.ps1 dashboard"
    Write-Host "  예시 2: .\scripts\server-admin.ps1 doctor"
    Write-Host "  예시 3: .\scripts\server-admin.ps1 logs --lines 30"
    Write-Host "  예시 4: .\scripts\server-admin.ps1 settings --interactive"
    Write-Host "  예시 5: .\scripts\server-admin.ps1 status"
    Write-Host "  예시 6: .\scripts\server-admin.ps1 bootstrap-admin --login-id admin --password secret123!"
    Write-Host "  예시 7: .\scripts\server-admin.ps1 list-members"
    Write-Host ""
    & $pythonExe $scriptPath --help
    exit $LASTEXITCODE
}

Set-Location $root
& $pythonExe $scriptPath @Arguments
