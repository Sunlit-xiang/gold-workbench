param([int]$Port = 3012)
$ErrorActionPreference = 'Stop'
$oracleProject = Split-Path -Parent $PSScriptRoot
$oracleNode = (Get-Command node).Source
$oracleLogs = Join-Path $oracleProject 'research_data\logs'
New-Item -ItemType Directory -Force -Path $oracleLogs | Out-Null
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw "Port $Port is already in use; no existing process was stopped." }
$env:PORT = "$Port"
$env:PYTHON_COMMAND = (Get-Command python).Source
$process = Start-Process -FilePath $oracleNode -ArgumentList 'server.mjs' -WorkingDirectory (Join-Path $oracleProject 'web') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $oracleLogs "web-$Port.out.log") -RedirectStandardError (Join-Path $oracleLogs "web-$Port.err.log")
[pscustomobject]@{ProcessId=$process.Id; Url="http://127.0.0.1:$Port/asset.html?asset=gold"}
