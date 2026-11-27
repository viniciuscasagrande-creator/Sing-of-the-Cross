# ============================================================================
# SIGN OF THE CROSS (SOTC) — V0.7 THE SENTINEL
# Script de Instalação do Agente Contínuo no Windows 11 (Tarefa Agendada)
# ============================================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = if (Test-Path "C:\laragon\bin\python\python-3.13\python.exe") {
    "C:\laragon\bin\python\python-3.13\python.exe"
} else {
    (Get-Command python -ErrorAction Stop).Source
}
$SentinelScript = Join-Path $PSScriptRoot "sentinel.py"
$TaskName = "SOTC_Sentinel_Agent_V07"

Write-Host "=================================================================" -ForegroundColor Red
Write-Host "  SIGN OF THE CROSS - INSTALADOR THE SENTINEL AGENT (V0.7)" -ForegroundColor Gray
Write-Host "=================================================================" -ForegroundColor Red
Write-Host "Python detectado: $PythonExe"
Write-Host "Script Sentinel : $SentinelScript"

$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$SentinelScript`"" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Sign Of The Cross V0.7 - The Sentinel Continuous Multi-Cloud Telemetry Agent" -Force | Out-Null

Write-Host "`n[OK] Tarefa agendada '$TaskName' instalada com sucesso no Windows 11!" -ForegroundColor Green
Write-Host "Para iniciar imediatamente em segundo plano: Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Yellow
