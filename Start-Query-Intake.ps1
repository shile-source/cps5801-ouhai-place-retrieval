$ErrorActionPreference = 'Stop'
if (Get-NetTCPConnection -LocalPort 8776 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host '8776 already listening; verify existing service rather than starting a duplicate.'
    exit 0
}
& (Join-Path $PSScriptRoot 'Start-Project.ps1') -PythonArgs @('-u','-m','src.demo.prospective_query_server')
exit $LASTEXITCODE
