# Starts the local review snapshot. Run Start-Project.ps1 for other project tasks.
& (Join-Path $PSScriptRoot 'Start-Project.ps1') -PythonArgs @(
    '-u', '-m', 'src.demo.server',
    '--port', '8770',
    '--corpus', 'data/clean/research_review_v0_5_20261125/poi_candidates.json',
    '--enable-bge', '--safe-streaming',
    '--dense-precision', 'float16',
    '--facts-binding', 'configs/research_v0_5_facts_binding.json'
)
exit $LASTEXITCODE
