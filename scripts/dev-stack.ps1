param(
    [string]$HostAddress = "",
    [int]$Port = 0,
    [int]$WaitMilliseconds = 1200,
    [switch]$Preview
)

$scriptsRoot = $PSScriptRoot
$root = Split-Path -Parent $scriptsRoot
. (Join-Path $scriptsRoot "common\_console_utf8.ps1")
$serverScript = Join-Path $scriptsRoot "dev-server.ps1"
$clientScript = Join-Path $scriptsRoot "dev-client.ps1"
$powershellExe = (Get-Command powershell.exe -ErrorAction Stop).Source
$envPath = Join-Path $root ".env"
$resolvedHostAddress = if ($HostAddress) { $HostAddress } else { Get-DotEnvValue -EnvPath $envPath -Key "SERVER_HOST" -DefaultValue "127.0.0.1" }
$resolvedPort = if ($Port -gt 0) { $Port } else { [int](Get-DotEnvValue -EnvPath $envPath -Key "SERVER_PORT" -DefaultValue "8011") }

if (-not (Test-Path $serverScript)) {
    Write-Error "서버 실행 스크립트를 찾을 수 없습니다: $serverScript"
    exit 1
}

if (-not (Test-Path $clientScript)) {
    Write-Error "클라이언트 실행 스크립트를 찾을 수 없습니다: $clientScript"
    exit 1
}

$serverArguments = @(
    '-NoExit',
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $serverScript,
    '-HostAddress', $resolvedHostAddress,
    '-Port', "$resolvedPort"
)

$clientArguments = @(
    '-NoExit',
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $clientScript
)

Write-Host ''
Write-Host 'CAPS 개발 스택 실행' -ForegroundColor Cyan
Write-Host "  서버: http://$resolvedHostAddress`:$resolvedPort"
Write-Host "  서버 스크립트: $serverScript"
Write-Host "  클라이언트 스크립트: $clientScript"
Write-Host "  서버 대기: ${WaitMilliseconds}ms"
Write-Host ''

if ($Preview) {
    Write-Host '미리보기 모드입니다. 실제 프로세스는 시작하지 않습니다.' -ForegroundColor Yellow
    Write-Host "  powershell.exe $($serverArguments -join ' ')"
    Write-Host "  powershell.exe $($clientArguments -join ' ')"
    exit 0
}

$serverProcess = Start-Process `
    -FilePath $powershellExe `
    -ArgumentList $serverArguments `
    -WorkingDirectory $root `
    -PassThru

Start-Sleep -Milliseconds $WaitMilliseconds

$clientProcess = Start-Process `
    -FilePath $powershellExe `
    -ArgumentList $clientArguments `
    -WorkingDirectory $root `
    -PassThru

Write-Host '개발 스택을 시작했습니다.' -ForegroundColor Green
Write-Host "  서버 PID: $($serverProcess.Id)"
Write-Host "  클라이언트 PID: $($clientProcess.Id)"
Write-Host ''
Write-Host '종료 방법' -ForegroundColor Cyan
Write-Host "  각 창을 직접 닫거나 Stop-Process -Id $($serverProcess.Id),$($clientProcess.Id)"
