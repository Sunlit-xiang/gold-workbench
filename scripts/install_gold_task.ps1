param([string]$TaskName = 'DigitalOracle-Gold-Daily')
$ErrorActionPreference = 'Stop'
$oracleScript = Join-Path $PSScriptRoot 'run_gold_daily.ps1'
$oraclePrincipal = [Security.Principal.WindowsIdentity]::GetCurrent().Name
# UTC EOD cohort, unrelated to New York DST. This host uses China Standard Time.
if ((Get-TimeZone).Id -ne 'China Standard Time') { throw 'Review local trigger timezone before installing on this host.' }
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) { throw 'Task already exists; inspect it before updating. Not overwritten.' }
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -File "' + $oracleScript + '"')
$trigger = New-ScheduledTaskTrigger -Daily -At '14:10'
$principal = New-ScheduledTaskPrincipal -UserId $oraclePrincipal -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'GC Proxy research shadow: collect, freeze and append outcomes. No Codex runtime dependency; requires signed-in Windows user.' | Select-Object TaskName,State
