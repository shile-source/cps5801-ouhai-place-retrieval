# Starts the local review snapshot. Run Start-Project.ps1 for other project tasks.
& (Join-Path $PSScriptRoot 'Start-Project.ps1') -PythonArgs @(
    '-u', '-m', 'src.demo.server',
    '--port', '8770',
    '--corpus', 'data/clean/activity_review_v0_6_20261126/poi_candidates.json',
    '--enable-bge', '--safe-streaming',
    '--dense-precision', 'float16',
    '--facts-binding', 'configs/activity_v0_6_facts_binding.json'
)
exit $LASTEXITCODE
