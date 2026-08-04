# Vigil — Chocolatey install script. Roadmap X21.
$ErrorActionPreference = 'Stop'

$toolsDir   = Split-Path -Parent $MyInvocation.MyCommand.Definition
$packageName = 'vigil'
$version     = '0.2.1'
$artifactRevision = '1.1'
$urlBase     = "https://github.com/SysAdminDoc/Vigil/releases/download/v$version"

$packageArgs = @{
  packageName    = $packageName
  fileType       = 'EXE'
  url            = "$urlBase/ungoogled-chromium_145.0.7632.159-$artifactRevision`_installer_x86.exe"
  url64bit       = "$urlBase/ungoogled-chromium_145.0.7632.159-$artifactRevision`_installer_x64.exe"
  # Hashes are filled in by CI before `choco push`. Treat the literal zeros as
  # placeholder; if you see them in the published package, file a release bug.
  checksum       = '0000000000000000000000000000000000000000000000000000000000000000'
  checksum64     = '0000000000000000000000000000000000000000000000000000000000000000'
  checksumType   = 'sha256'
  checksumType64 = 'sha256'
  silentArgs     = '--do-not-launch-chrome'
  validExitCodes = @(0)
}

Install-ChocolateyPackage @packageArgs
