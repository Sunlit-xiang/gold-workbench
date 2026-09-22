$ErrorActionPreference = 'Stop'
$oracleTaskName = 'DigitalOracle-Gold-Workbench'
if (Get-ScheduledTask -TaskName $oracleTaskName -ErrorAction SilentlyContinue) { throw 'Workbench task already exists; not overwritten.' }
$oraclePrincipal = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$oracleScript = Join-Path $PSScriptRoot 'start_gold_workbench.ps1'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -File "' + $oracleScript + '" -Port 3012')
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $oraclePrincipal
$principal = New-ScheduledTaskPrincipal -UserId $oraclePrincipal -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $oracleTaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Start the local Gold research workbench at Windows sign-in; no Codex dependency.' | Select-Object TaskName,State
