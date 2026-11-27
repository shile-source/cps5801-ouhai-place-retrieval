# Starts the local review snapshot. A recorded stop is not cleared by restarting.
param([switch]$LexicalOnly)
# Socket probing also works where Windows CIM/network enumeration is restricted.
& (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') -c 'import socket,sys; s=socket.socket(); s.settimeout(2); result=s.connect_ex(("127.0.0.1",8770)); s.close(); sys.exit(0 if result==0 else 1 if result in (10061,111) else 2)'
if ($LASTEXITCODE -eq 0) {
    Write-Host '8770 already listening; do not duplicate. http://127.0.0.1:8770/'
    exit 0
}
if ($LASTEXITCODE -ne 1) { throw 'Cannot verify the local port; no duplicate service started.' }
if ((Test-Path -LiteralPath (Join-Path $PSScriptRoot 'outputs/model_stop_checkpoint_20261127.json')) -and -not $LexicalOnly) {
    & (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'src\demo\runtime_policy.py')
    if ($LASTEXITCODE -ne 0) { throw 'No validated changed-configuration receipt. Use -LexicalOnly; no model retry performed.' }
}
$demoArguments = @(
    '-u', '-m', 'src.demo.server',
    '--port', '8770',
    '--corpus', 'data/clean/activity_review_v0_6_20261126/poi_candidates.json',
    '--safe-streaming',
    '--dense-precision', 'float16',
    '--dense-idle-seconds', '60',
    '--stop-checkpoint', 'outputs/residency_repair_20261127/runtime_stop.json',
    '--facts-binding', 'configs/activity_v0_6_facts_binding.json'
)
if ($LexicalOnly) { $demoArguments += '--disable-encoder' } else { $demoArguments += '--enable-bge' }
& (Join-Path $PSScriptRoot 'Start-Project.ps1') -PythonArgs $demoArguments
exit $LASTEXITCODE
