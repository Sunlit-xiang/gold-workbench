$ErrorActionPreference = 'Stop'
$oracleProject = Split-Path -Parent $PSScriptRoot
$oraclePython = if ($env:PYTHON_COMMAND) { $env:PYTHON_COMMAND } else { (Get-Command python).Source }
$oracleLogDirectory = Join-Path $oracleProject 'research_data\logs'
New-Item -ItemType Directory -Force -Path $oracleLogDirectory | Out-Null
$oracleLogPath = Join-Path $oracleLogDirectory ('daily-' + (Get-Date -Format 'yyyy-MM-dd') + '.log')
$env:PYTHONIOENCODING = 'utf-8'
Push-Location $oracleProject
try {
    & $oraclePython 'scripts/asset_pipeline.py' daily 2>&1 | Out-File -LiteralPath $oracleLogPath -Encoding utf8 -Append
    if ($LASTEXITCODE -ne 0) { throw "Gold pipeline failed. See $oracleLogPath" }
} finally { Pop-Location }
