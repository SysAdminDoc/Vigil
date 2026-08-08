[CmdletBinding()]
param(
  [string]$KioskUrl = ''
)

$ErrorActionPreference = 'Stop'

function Get-PolicyKioskUrl {
  $policyPath = 'HKLM:\Software\Policies\Vigil'
  try {
    $policy = Get-ItemProperty -LiteralPath $policyPath -Name 'VigilKioskUrl' -ErrorAction Stop
    return [string]$policy.VigilKioskUrl
  } catch {
    return ''
  }
}

function Resolve-KioskUrl {
  param([string]$Candidate)

  $value = $Candidate.Trim()
  if ([string]::IsNullOrWhiteSpace($value)) {
    $value = Get-PolicyKioskUrl
  }
  if ([string]::IsNullOrWhiteSpace($value)) {
    return 'about:blank'
  }
  if ($value.Length -gt 2048 -or $value.IndexOfAny([char[]]"`r`n`t") -ge 0) {
    throw 'Kiosk URL is too long or contains control characters.'
  }
  if ($value -eq 'about:blank') {
    return $value
  }

  $uri = $null
  if (-not [System.Uri]::TryCreate($value, [System.UriKind]::Absolute, [ref]$uri)) {
    throw 'Kiosk URL must be an absolute HTTPS URL or about:blank.'
  }
  if ($uri.Scheme -ne 'https' -or [string]::IsNullOrWhiteSpace($uri.Host) -or
      -not [string]::IsNullOrEmpty($uri.UserInfo) -or $uri.IsFile) {
    throw 'Kiosk URL must be an absolute HTTPS URL or about:blank.'
  }
  return $uri.AbsoluteUri
}

function Resolve-ChromePath {
  $candidates = @(
    (Join-Path (Split-Path $PSScriptRoot -Parent) 'chrome.exe'),
    (Join-Path ${env:ProgramFiles} 'Vigil\Application\chrome.exe')
  )
  foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
      return (Resolve-Path -LiteralPath $candidate).Path
    }
  }
  throw 'Could not find chrome.exe next to the launcher or in Program Files.'
}

$resolvedUrl = Resolve-KioskUrl $KioskUrl
$chromePath = Resolve-ChromePath
$dataRoot = Join-Path ${env:LOCALAPPDATA} 'Vigil-Kiosk'
$userDataDir = Join-Path $dataRoot 'UserData'
$cacheDir = Join-Path $dataRoot 'Cache'
New-Item -ItemType Directory -Path $userDataDir, $cacheDir -Force | Out-Null

$arguments = @(
  '--kiosk',
  '--no-first-run',
  '--no-default-browser-check',
  '--disable-pinch',
  '--disable-features=TranslateUI',
  '--noerrdialogs',
  '--disable-session-crashed-bubble',
  '--disable-infobars',
  '--overscroll-history-navigation=0',
  '--check-for-update-interval=31536000',
  "--user-data-dir=$userDataDir",
  "--disk-cache-dir=$cacheDir",
  $resolvedUrl
)

$process = Start-Process -FilePath $chromePath -ArgumentList $arguments `
  -WorkingDirectory (Split-Path $chromePath -Parent) -PassThru -Wait
exit $process.ExitCode
