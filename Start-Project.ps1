param([Parameter(ValueFromRemainingArguments=$true)][string[]]$PythonArgs)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$env:PIP_CACHE_DIR = Join-Path $projectRoot '.cache\pip'
$env:HF_HOME = Join-Path $projectRoot '.cache\huggingface'
$env:HF_HUB_CACHE = Join-Path $env:HF_HOME 'hub'
$env:HF_XET_CACHE = Join-Path $env:HF_HOME 'xet'
$env:HF_ASSETS_CACHE = Join-Path $env:HF_HOME 'assets'
$env:HF_DATASETS_CACHE = Join-Path $env:HF_HOME 'datasets'
$env:SENTENCE_TRANSFORMERS_HOME = $env:HF_HUB_CACHE
$env:TORCH_HOME = Join-Path $projectRoot '.cache\torch'
$env:TORCH_EXTENSIONS_DIR = Join-Path $env:TORCH_HOME 'extensions'
$env:CUDA_CACHE_PATH = Join-Path $env:TORCH_HOME 'cuda_compute_cache'
$env:XDG_CACHE_HOME = Join-Path $projectRoot '.cache'
$env:TMP = Join-Path $projectRoot '.cache\tmp'
$env:TEMP = $env:TMP
$env:TMPDIR = $env:TMP
$env:PYTHONPATH = $projectRoot
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:NUMEXPR_NUM_THREADS = '1'
foreach ($cachePath in @($env:PIP_CACHE_DIR,$env:HF_HOME,$env:HF_HUB_CACHE,$env:HF_XET_CACHE,$env:HF_ASSETS_CACHE,$env:HF_DATASETS_CACHE,$env:TORCH_HOME,$env:TORCH_EXTENSIONS_DIR,$env:CUDA_CACHE_PATH,$env:TMP)) {
    New-Item -ItemType Directory -Path $cachePath -Force | Out-Null
}
Set-Location $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $pythonPath)) { throw 'Project .venv is missing.' }
if ($PythonArgs.Count -gt 0) {
    & $pythonPath @PythonArgs
    exit $LASTEXITCODE
}
Write-Host "Python: $pythonPath"
Write-Host "Cache: $env:PIP_CACHE_DIR; Temp: $env:TEMP"
Write-Host 'Usage: .\Start-Project.ps1 -m pytest -q'
