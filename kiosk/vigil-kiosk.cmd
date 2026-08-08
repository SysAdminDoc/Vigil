@echo off
rem ----------------------------------------------------------------------
rem Vigil-Kiosk launcher. Roadmap X12.
rem
rem Usage: vigil-kiosk.cmd
rem        vigil-kiosk.cmd https://patient-portal.example.com
rem
rem Boots Vigil directly into a single validated HTTPS URL with the chrome UI
rem hidden. URL parsing and Chromium argument construction live in the paired
rem PowerShell launcher so cmd metacharacters cannot become launcher options.
rem
rem Pair with kiosk\install-watchdog.ps1 to auto-restart on crash and
rem with the VigilKioskUrl ADMX policy to remotely-configure the URL.
rem ----------------------------------------------------------------------

setlocal

if not "%~2"=="" (
  echo Usage: vigil-kiosk.cmd [https://host/path]
  exit /b 2
)

set "LAUNCHER=%~dp0vigil-kiosk.ps1"
if not exist "%LAUNCHER%" (
  echo Could not find the PowerShell kiosk launcher: %LAUNCHER%
  exit /b 1
)

if "%~1"=="" (
  powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%LAUNCHER%"
) else (
  powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%LAUNCHER%" -KioskUrl "%~1"
)

endlocal
exit /b %ERRORLEVEL%
