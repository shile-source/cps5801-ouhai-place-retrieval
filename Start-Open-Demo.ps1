# OSM-only public reproducibility demonstration. Models remain paused by default.
& (Join-Path $PSScriptRoot 'Start-Project.ps1') -PythonArgs @(
    '-u','-m','src.demo.server','--port','8774',
    '--corpus','data/clean/open_osm_v2_20261126/poi_candidates.json',
    '--disable-encoder'
)
exit $LASTEXITCODE
