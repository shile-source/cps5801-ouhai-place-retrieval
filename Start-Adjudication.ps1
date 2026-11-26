# This author's private frozen12-case review; does not create human judgments.
& (Join-Path $PSScriptRoot 'Start-Project.ps1') -PythonArgs @(
    '-u','-m','src.demo.adjudication_server','--port','8775',
    '--session','data/labels/adjudication_first_rater_12_v1_20261126'
)
exit $LASTEXITCODE
