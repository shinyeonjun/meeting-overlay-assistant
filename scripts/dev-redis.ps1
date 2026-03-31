param(
    [ValidateSet("up", "down", "logs", "ps", "restart", "redis-cli", "status")]
    [string]$Action = "up"
)

$scriptsRoot = $PSScriptRoot
$infraScript = Join-Path $scriptsRoot "dev-infra.ps1"

if (-not (Test-Path $infraScript)) {
    Write-Error "공통 인프라 스크립트를 찾을 수 없습니다: $infraScript"
    exit 1
}

$mappedAction = if ($Action -eq "ps") { "status" } else { $Action }
& $infraScript -Action $mappedAction -Service redis
