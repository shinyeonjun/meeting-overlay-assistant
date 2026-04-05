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
