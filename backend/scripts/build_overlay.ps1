param()

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$frontendRoot = Join-Path $projectRoot "frontend"

Push-Location $frontendRoot
try {
    npm install
    npm run overlay:build
}
finally {
    Pop-Location
}
