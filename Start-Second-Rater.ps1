# Separate second-rater collection; never starts a model or copies old grades.
& (Join-Path $PSScriptRoot 'Start-Project.ps1') -PythonArgs @('-u','-m','src.demo.second_rater_server')
exit $LASTEXITCODE
