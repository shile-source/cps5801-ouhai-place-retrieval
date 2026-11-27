# Starts the local review snapshot. A recorded stop is not cleared by restarting.
param([switch]$LexicalOnly)
if (Get-NetTCPConnection -LocalPort 8770 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host '8770 already listening; do not duplicate. http://127.0.0.1:8770/'
    exit 0
}
if ((Test-Path -LiteralPath (Join-Path $PSScriptRoot 'outputs/model_stop_checkpoint_20261127.json')) -and -not $LexicalOnly) {
    throw 'The recorded model stop requires investigation and a newly authorized changed check. Use -LexicalOnly to browse/search without models. No retry performed.'
}
$demoArguments = @(
    '-u', '-m', 'src.demo.server',
    '--port', '8770',
    '--corpus', 'data/clean/activity_review_v0_6_20261126/poi_candidates.json',
    '--safe-streaming',
    '--dense-precision', 'float16',
    '--facts-binding', 'configs/activity_v0_6_facts_binding.json'
)
if ($LexicalOnly) { $demoArguments += '--disable-encoder' } else { $demoArguments += '--enable-bge' }
& (Join-Path $PSScriptRoot 'Start-Project.ps1') -PythonArgs $demoArguments
exit $LASTEXITCODE
