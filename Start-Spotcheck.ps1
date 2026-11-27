$ErrorActionPreference = 'Stop'
if (Get-NetTCPConnection -LocalPort 8778 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host '8778 already listening; do not duplicate.'
    exit 0
}
& (Join-Path $PSScriptRoot 'Start-Project.ps1') -PythonArgs @('-u','-m','src.demo.spotcheck_server')
exit $LASTEXITCODE
