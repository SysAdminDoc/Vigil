[CmdletBinding()]
param(
  [string]$KioskUrl = '',
  [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'
$TaskName = 'Vigil-Kiosk Watchdog'
$EventSource = 'Vigil-Kiosk'
$PolicyPath = 'HKLM:\Software\Policies\Vigil'
$ProgramDataRoot = Join-Path ${env:ProgramData} 'Vigil'
$WrapperPath = Join-Path $ProgramDataRoot 'kiosk-watchdog.ps1'
$ConfigPath = Join-Path $ProgramDataRoot 'kiosk-watchdog.json'
$StatePath = Join-Path $ProgramDataRoot 'kiosk-watchdog-state.json'
$LauncherPath = (Resolve-Path (Join-Path $PSScriptRoot 'vigil-kiosk.cmd')).Path
$WrapperTemplate = (Resolve-Path (Join-Path $PSScriptRoot 'kiosk-watchdog.ps1')).Path

function Read-State {
  if (-not (Test-Path -LiteralPath $StatePath -PathType Leaf)) { return $null }
  try {
    return Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
  } catch {
    throw "Owned kiosk state is unreadable: $StatePath"
  }
}

function Write-JsonAtomic {
  param([string]$Path, [object]$Value)

  $temporary = "$Path.$([System.IO.Path]::GetRandomFileName()).tmp"
  $Value | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $temporary -Encoding UTF8
  Move-Item -LiteralPath $temporary -Destination $Path -Force
}

function Get-ValidatedKioskUrl {
  param([string]$Candidate)

  $value = $Candidate.Trim()
  if ([string]::IsNullOrWhiteSpace($value)) { return '' }
  if ($value.Length -gt 2048 -or $value.IndexOfAny([char[]]"`r`n`t") -ge 0) {
    throw 'Kiosk URL is too long or contains control characters.'
  }
  if ($value -eq 'about:blank') { return $value }

  $uri = $null
  if (-not [System.Uri]::TryCreate($value, [System.UriKind]::Absolute, [ref]$uri) -or
      $uri.Scheme -ne 'https' -or [string]::IsNullOrWhiteSpace($uri.Host) -or
      -not [string]::IsNullOrEmpty($uri.UserInfo) -or $uri.IsFile) {
    throw 'Kiosk URL must be an absolute HTTPS URL or about:blank.'
  }
  return $uri.AbsoluteUri
}

function Ensure-EventSource {
  if ([System.Diagnostics.EventLog]::SourceExists($EventSource)) { return $false }
  [System.Diagnostics.EventLog]::CreateEventSource($EventSource, 'Application')
  return $true
}

function Get-PolicyValue {
  try {
    return (Get-ItemProperty -LiteralPath $PolicyPath -Name 'VigilKioskUrl' -ErrorAction Stop).VigilKioskUrl
  } catch {
    return $null
  }
}

function Remove-EmptyPolicyKey {
  if (-not (Test-Path -LiteralPath $PolicyPath)) { return }
  $properties = Get-ItemProperty -LiteralPath $PolicyPath
  $ownedProperties = @($properties.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' })
  $children = @(Get-ChildItem -LiteralPath $PolicyPath -ErrorAction SilentlyContinue)
  if ($ownedProperties.Count -eq 0 -and $children.Count -eq 0) {
    Remove-Item -LiteralPath $PolicyPath -Force
  }
}

function Uninstall-Watchdog {
  $state = Read-State
  $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  if ($null -ne $task) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed scheduled task '$TaskName'."
  }

  foreach ($path in @($WrapperPath, $ConfigPath)) {
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
  }

  if ($null -ne $state -and [bool]$state.owned_policy_value) {
    $current = Get-PolicyValue
    if ([string]$current -eq [string]$state.installed_policy_value) {
      if ([bool]$state.had_previous_policy_value) {
        Set-ItemProperty -LiteralPath $PolicyPath -Name 'VigilKioskUrl' `
          -Value ([string]$state.previous_policy_value) -Type String
      } else {
        Remove-ItemProperty -LiteralPath $PolicyPath -Name 'VigilKioskUrl' -Force -ErrorAction SilentlyContinue
      }
      Remove-EmptyPolicyKey
      Write-Host 'Removed the installer-owned VigilKioskUrl policy value.'
    } else {
      Write-Warning 'VigilKioskUrl changed after installation; leaving the current policy value intact.'
    }
  }

  if ($null -ne $state -and [bool]$state.created_event_source) {
    $eventSourceKey = "HKLM:\SYSTEM\CurrentControlSet\Services\EventLog\Application\$EventSource"
    if (Test-Path -LiteralPath $eventSourceKey) {
      Remove-Item -LiteralPath $eventSourceKey -Recurse -Force
      Write-Host "Removed event-log source '$EventSource'."
    }
  }
  if (Test-Path -LiteralPath $StatePath) { Remove-Item -LiteralPath $StatePath -Force }
  if (Test-Path -LiteralPath $ProgramDataRoot) {
    $remaining = @(Get-ChildItem -LiteralPath $ProgramDataRoot -Force)
    if ($remaining.Count -eq 0) { Remove-Item -LiteralPath $ProgramDataRoot -Force }
  }
  Write-Host 'Vigil-Kiosk watchdog uninstall complete.'
}

if ($Uninstall) {
  Uninstall-Watchdog
  exit 0
}

if (-not (Test-Path -LiteralPath $LauncherPath -PathType Leaf)) {
  throw "Launcher not found: $LauncherPath"
}
if (-not (Test-Path -LiteralPath $WrapperTemplate -PathType Leaf)) {
  throw "Watchdog template not found: $WrapperTemplate"
}

$validatedUrl = Get-ValidatedKioskUrl $KioskUrl
$oldState = Read-State
$currentPolicyValue = Get-PolicyValue
$hadPreviousPolicyValue = $null -ne $currentPolicyValue
$previousPolicyValue = [string]$currentPolicyValue
if ($null -ne $oldState -and [bool]$oldState.owned_policy_value -and
    [string]$currentPolicyValue -eq [string]$oldState.installed_policy_value) {
  $hadPreviousPolicyValue = [bool]$oldState.had_previous_policy_value
  $previousPolicyValue = [string]$oldState.previous_policy_value
}

$createdEventSource = $false
if (-not [System.Diagnostics.EventLog]::SourceExists($EventSource)) {
  $createdEventSource = Ensure-EventSource
}

New-Item -ItemType Directory -Path $ProgramDataRoot -Force | Out-Null
Copy-Item -LiteralPath $WrapperTemplate -Destination $WrapperPath -Force
$config = [ordered]@{
  schema_version = 1
  launcher_path = $LauncherPath
  max_restart_attempts = 5
  restart_window_seconds = 900
  stable_run_seconds = 300
  base_backoff_seconds = 5
  max_backoff_seconds = 60
}
Write-JsonAtomic $ConfigPath $config

$ownedPolicyValue = $false
$installedPolicyValue = ''
if (-not [string]::IsNullOrWhiteSpace($validatedUrl)) {
  if (-not (Test-Path -LiteralPath $PolicyPath)) {
    New-Item -Path $PolicyPath -Force | Out-Null
  }
  Set-ItemProperty -LiteralPath $PolicyPath -Name 'VigilKioskUrl' -Value $validatedUrl -Type String
  $ownedPolicyValue = $true
  $installedPolicyValue = $validatedUrl
  Write-Host 'Set installer-owned VigilKioskUrl policy.'
} elseif ($null -ne $oldState -and [bool]$oldState.owned_policy_value -and
          [string]$currentPolicyValue -eq [string]$oldState.installed_policy_value) {
  $ownedPolicyValue = $true
  $installedPolicyValue = [string]$oldState.installed_policy_value
}

$state = [ordered]@{
  schema_version = 1
  owned_policy_value = $ownedPolicyValue
  installed_policy_value = $installedPolicyValue
  had_previous_policy_value = $hadPreviousPolicyValue
  previous_policy_value = $previousPolicyValue
  created_event_source = $createdEventSource
}
Write-JsonAtomic $StatePath $state

$powerShellPath = Join-Path $PSHOME 'powershell.exe'
$action = New-ScheduledTaskAction `
  -Execute $powerShellPath `
  -Argument "-NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$WrapperPath`" -ConfigPath `"$ConfigPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable `
  -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -GroupId 'INTERACTIVE' -RunLevel Highest

Register-ScheduledTask `
  -TaskName $TaskName `
  -Description 'Vigil-Kiosk watchdog with bounded restart recovery.' `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Principal $principal `
  -Force | Out-Null

Write-Host "Installed scheduled task '$TaskName'."
Write-Host 'Vigil-Kiosk will launch at the next interactive logon.'
