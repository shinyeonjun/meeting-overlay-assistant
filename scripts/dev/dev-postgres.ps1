# 개발 실행 스크립트에서 dev postgres 작업을 수행한다.
ì ìííë¤.
param(
    [ValidateSet("up", "down", "logs", "psql", "status", "restart")]
    [string]$Action = "up"
)

$scriptsRoot = $PSScriptRoot
$infraScript = Join-Path $scriptsRoot "dev-infra.ps1"

if (-not (Test-Path $infraScript)) {
    Write-Error "Common infra script not found: $infraScript"
    exit 1
}

& $infraScript -Action $Action -Service postgresql
