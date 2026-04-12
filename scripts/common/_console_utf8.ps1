$utf8Encoding = New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding = $utf8Encoding
[Console]::OutputEncoding = $utf8Encoding
$OutputEncoding = $utf8Encoding
$env:PYTHONIOENCODING = "utf-8"
$null = cmd.exe /c "chcp 65001 > nul"

function Get-DotEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$EnvPath,
        [Parameter(Mandatory = $true)]
        [string]$Key,
        [string]$DefaultValue = ""
    )

    if (-not (Test-Path $EnvPath)) {
        return $DefaultValue
    }

    $pattern = '^\s*' + [Regex]::Escape($Key) + '=(.*)$'
    foreach ($line in Get-Content -Path $EnvPath -Encoding UTF8) {
        if ($line -match $pattern) {
            return $matches[1].Trim()
        }
    }

    return $DefaultValue
}
