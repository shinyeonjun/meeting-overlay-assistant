# 개발 실행 스크립트에서 dev redis 작업을 수행한다.
ì ìííë¤.
param(
    [ValidateSet("up", "down", "logs", "ps", "restart", "redis-cli", "status")]
    [string]$Action = "up"
)

$scriptsRoot = $PSScriptRoot
$infraScript = Join-Path $scriptsRoot "dev-infra.ps1"

if (-not (Test-Path $infraScript)) {
    Write-Error "Common infra script not found: $infraScript"
    exit 1
}

$mappedAction = if ($Action -eq "ps") { "status" } else { $Action }
& $infraScript -Action $mappedAction -Service redis
