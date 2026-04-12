param(
    [string]$HostAddress = "",
    [int]$Port = 0
)

$scriptsRoot = $PSScriptRoot
$root = Split-Path -Parent $scriptsRoot
. (Join-Path $scriptsRoot "common\_console_utf8.ps1")
$pythonExe = Join-Path $root "venv\Scripts\python.exe"
$envPath = Join-Path $root ".env"
$resolvedHostAddress = if ($HostAddress) { $HostAddress } else { Get-DotEnvValue -EnvPath $envPath -Key "SERVER_HOST" -DefaultValue "127.0.0.1" }
$resolvedPort = if ($Port -gt 0) { $Port } else { [int](Get-DotEnvValue -EnvPath $envPath -Key "SERVER_PORT" -DefaultValue "8011") }

if (-not (Test-Path $pythonExe)) {
    Write-Error "가상환경 Python을 찾을 수 없습니다: $pythonExe"
    exit 1
}

Write-Host ""
Write-Host "CAPS 개발 서버 시작" -ForegroundColor Cyan
Write-Host "  루트:   $root"
Write-Host "  주소:   http://$resolvedHostAddress`:$resolvedPort"
Write-Host "  앱:     server.app.main:app"
Write-Host ""

Set-Location $root
& $pythonExe -m uvicorn server.app.main:app --host $resolvedHostAddress --port $resolvedPort
