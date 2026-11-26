# New evidence-filter UI without permitting either paused GPU model to restart.
& (Join-Path $PSScriptRoot 'Start-Project.ps1') -PythonArgs @(
    '-u','-m','src.demo.server','--port','8773',
    '--corpus','data/clean/research_review_v0_5_20261125/poi_candidates.json',
    '--enable-bge','--safe-streaming','--disable-encoder',
    '--facts-binding','configs/research_v0_5_facts_binding.json'
)
exit $LASTEXITCODE
