[CmdletBinding()]
param(
  [string]$ConfigPath = (Join-Path $PSScriptRoot 'kiosk-watchdog.json')
)

$ErrorActionPreference = 'Stop'
$EventSource = 'Vigil-Kiosk'
$MaxEventMessageLength = 512

function Write-KioskEvent {
  param(
    [int]$EventId,
    [System.Diagnostics.EventLogEntryType]$EntryType,
    [string]$Message
  )

  if ($null -eq $Message) { $Message = '' }
  $bounded = if ($Message.Length -gt $MaxEventMessageLength) {
    $Message.Substring(0, $MaxEventMessageLength)
  } else {
    $Message
  }
  try {
    Write-EventLog -LogName Application -Source $EventSource -EventId $EventId `
      -EntryType $EntryType -Message $bounded
  } catch {
    # Event logging must never turn a kiosk recovery loop into another crash.
  }
}

function Get-BoundedInt {
  param(
    [object]$Value,
    [int]$Default,
    [int]$Minimum,
    [int]$Maximum
  )

  $number = 0
  if (-not [int]::TryParse([string]$Value, [ref]$number)) { return $Default }
  return [Math]::Max($Minimum, [Math]::Min($Maximum, $number))
}

if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
  Write-KioskEvent 1004 Error 'Watchdog configuration is missing.'
  exit 21
}

try {
  $config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
  $launcherPath = [System.IO.Path]::GetFullPath([string]$config.launcher_path)
  if ([System.IO.Path]::GetFileName($launcherPath) -ne 'vigil-kiosk.cmd' -or
      -not (Test-Path -LiteralPath $launcherPath -PathType Leaf)) {
    throw 'Launcher path is not the expected kiosk command file.'
  }
  $maxAttempts = Get-BoundedInt $config.max_restart_attempts 5 1 10
  $windowSeconds = Get-BoundedInt $config.restart_window_seconds 900 60 3600
  $stableRunSeconds = Get-BoundedInt $config.stable_run_seconds 300 60 3600
  $baseBackoffSeconds = Get-BoundedInt $config.base_backoff_seconds 5 1 60
  $maxBackoffSeconds = Get-BoundedInt $config.max_backoff_seconds 60 5 300
} catch {
  Write-KioskEvent 1004 Error 'Watchdog configuration is invalid.'
  exit 21
}

$restartTimes = [System.Collections.Generic.List[datetime]]::new()
while ($true) {
  $startedAt = Get-Date
  $exitCode = -1
  try {
    $process = Start-Process -FilePath $launcherPath -WorkingDirectory (Split-Path $launcherPath -Parent) `
      -WindowStyle Hidden -PassThru -Wait
    $exitCode = [int]$process.ExitCode
  } catch {
    $exitCode = -1
  }

  $runtime = ((Get-Date) - $startedAt).TotalSeconds
  if ($exitCode -eq 0) {
    Write-KioskEvent 1000 Information 'Vigil kiosk exited normally; watchdog stopped.'
    exit 0
  }
  if ($runtime -ge $stableRunSeconds) {
    $restartTimes.Clear()
  }

  $now = Get-Date
  while ($restartTimes.Count -gt 0 -and
         (($now - $restartTimes[0]).TotalSeconds -gt $windowSeconds)) {
    $restartTimes.RemoveAt(0)
  }
  if ($restartTimes.Count -ge $maxAttempts) {
    Write-KioskEvent 1003 Error 'Vigil kiosk restart circuit breaker opened.'
    exit 20
  }

  $restartTimes.Add($now)
  $attempt = $restartTimes.Count
  $delay = [int][Math]::Min(
    $maxBackoffSeconds,
    $baseBackoffSeconds * [Math]::Pow(2, $attempt - 1)
  )
  Write-KioskEvent 1001 Warning `
    ("Vigil kiosk exited with code {0}; restart attempt {1} of {2} in {3} seconds." `
      -f $exitCode, $attempt, $maxAttempts, $delay)
  Start-Sleep -Seconds $delay
}
