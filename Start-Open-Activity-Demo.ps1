# Public OSM-only activity demo. No private queries, labels or mixed data needed.
& (Join-Path $PSScriptRoot 'Start-Project.ps1') -PythonArgs @(
    '-u','-m','src.demo.server','--port','8779',
    '--corpus','data/clean/open_activity_v1_20261127/poi_candidates.json',
    '--facts-binding','configs/open_activity_study_binding_20261128.json',
    '--disable-encoder'
)
exit $LASTEXITCODE
