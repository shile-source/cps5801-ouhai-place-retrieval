$ErrorActionPreference = 'Stop'
if (Get-NetTCPConnection -LocalPort 8777 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host '8777 already listening; verify existing service, do not duplicate.'
    exit 0
}
& (Join-Path $PSScriptRoot 'Start-Project.ps1') -PythonArgs @('-u','-m','src.demo.assisted_review_server')
exit $LASTEXITCODE
