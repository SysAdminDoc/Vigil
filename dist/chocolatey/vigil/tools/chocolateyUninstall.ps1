# Vigil — Chocolatey uninstall script. Roadmap X21.
$ErrorActionPreference = 'Stop'

$packageName    = 'vigil'
$softwareName   = 'Vigil*'
$installerType  = 'EXE'
$silentArgs     = '--uninstall --force-uninstall --system-level'
$validExitCodes = @(0, 19)

[array]$keys = Get-UninstallRegistryKey -SoftwareName $softwareName
if ($keys.Count -eq 1) {
  $keys | ForEach-Object {
    $file = "$($_.UninstallString)"
    Uninstall-ChocolateyPackage `
      -PackageName  $packageName `
      -FileType     $installerType `
      -SilentArgs   $silentArgs `
      -ValidExitCodes $validExitCodes `
      -File         $file
  }
} elseif ($keys.Count -eq 0) {
  Write-Warning "$packageName has already been uninstalled by other means."
} else {
  Write-Warning "Multiple matches for $packageName uninstall keys; manual cleanup required."
  $keys | ForEach-Object { Write-Warning "- $($_.DisplayName) at $($_.UninstallString)" }
}
