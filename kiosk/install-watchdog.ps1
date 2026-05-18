# Vigil-Kiosk watchdog installer. Roadmap X12.
#
# Registers a Windows Task Scheduler task that:
#   1. Runs at user logon
#   2. Launches kiosk\vigil-kiosk.cmd
#   3. Restarts within 5 seconds if Vigil exits
#   4. Logs restarts to the Windows Application event log under source "Vigil-Kiosk"
#
# Run elevated:
#   powershell -ExecutionPolicy Bypass -File .\install-watchdog.ps1 -KioskUrl https://...
#
# Uninstall:
#   powershell -File .\install-watchdog.ps1 -Uninstall

param(
  [string]$KioskUrl = '',
  [string]$LauncherPath = (Join-Path $PSScriptRoot 'vigil-kiosk.cmd'),
  [string]$TaskName = 'Vigil-Kiosk Watchdog',
  [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'

function Ensure-EventSource {
  $src = 'Vigil-Kiosk'
  if (-not [System.Diagnostics.EventLog]::SourceExists($src)) {
    [System.Diagnostics.EventLog]::CreateEventSource($src, 'Application')
    Write-Host "Created event-log source '$src'."
  }
}

if ($Uninstall) {
  if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed scheduled task '$TaskName'."
  } else {
    Write-Host "No scheduled task '$TaskName' found."
  }
  exit 0
}

if (-not (Test-Path $LauncherPath)) {
  throw "Launcher not found: $LauncherPath"
}

Ensure-EventSource

# If a URL is provided, write it under HKLM\Software\Policies\Vigil so the launcher
# picks it up. The user can override per-launch by passing the URL as the first
# argument to vigil-kiosk.cmd.
if ($KioskUrl) {
  $policyKey = 'HKLM:\Software\Policies\Vigil'
  if (-not (Test-Path $policyKey)) { New-Item -Path $policyKey -Force | Out-Null }
  Set-ItemProperty -Path $policyKey -Name 'VigilKioskUrl' -Value $KioskUrl -Type String
  Write-Host "Set VigilKioskUrl policy: $KioskUrl"
}

# Build the watchdog action: launch the kiosk, and if it exits, restart.
$wrapperPs1 = @'
$ErrorActionPreference = "Continue"
while ($true) {
  $proc = Start-Process -FilePath "@LAUNCHER@" -PassThru -Wait
  $ec = $proc.ExitCode
  Write-EventLog -LogName Application -Source "Vigil-Kiosk" -EventId 1001 `
    -EntryType Warning -Message "Vigil exited with code $ec. Restarting in 5s."
  Start-Sleep -Seconds 5
}
'@.Replace('@LAUNCHER@', $LauncherPath)

$wrapperPath = Join-Path $env:ProgramData 'Vigil\kiosk-watchdog.ps1'
New-Item -Path (Split-Path $wrapperPath) -ItemType Directory -Force | Out-Null
Set-Content -Path $wrapperPath -Value $wrapperPs1 -Encoding UTF8

$action  = New-ScheduledTaskAction `
  -Execute 'powershell.exe' `
  -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$wrapperPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
  -RestartInterval (New-TimeSpan -Seconds 5) `
  -RestartCount 999 `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable

$principal = New-ScheduledTaskPrincipal `
  -GroupId 'INTERACTIVE' `
  -RunLevel Highest

Register-ScheduledTask `
  -TaskName $TaskName `
  -Description 'Vigil-Kiosk watchdog (Roadmap X12). Restarts Vigil on crash.' `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Principal $principal `
  -Force | Out-Null

Write-Host "Installed scheduled task '$TaskName'."
Write-Host "Vigil-Kiosk will launch at next interactive logon."
