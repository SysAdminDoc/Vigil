@echo off
rem ----------------------------------------------------------------------
rem Vigil-Kiosk launcher. Roadmap X12.
rem
rem Usage: vigil-kiosk.cmd
rem        vigil-kiosk.cmd https://patient-portal.example.com
rem
rem Boots Vigil directly into a single pinned URL with the chrome UI hidden.
rem Reads the VigilKioskUrl from HKLM\Software\Policies\Vigil if no argument
rem is passed; falls back to about:blank if neither is set.
rem
rem Pair with kiosk\install-watchdog.ps1 to auto-restart on crash and
rem with the VigilKioskUrl ADMX policy to remotely-configure the URL.
rem ----------------------------------------------------------------------

setlocal

set "CHROME_EXE=%~dp0..\chrome.exe"
if not exist "%CHROME_EXE%" set "CHROME_EXE=%ProgramFiles%\Vigil\Application\chrome.exe"
if not exist "%CHROME_EXE%" (
  echo Could not find chrome.exe next to %~dp0 or in %ProgramFiles%\Vigil\Application
  exit /b 1
)

rem ---- resolve URL ----
set "KIOSK_URL=%~1"
if not defined KIOSK_URL (
  for /f "tokens=2,*" %%A in (
    'reg query "HKLM\Software\Policies\Vigil" /v "VigilKioskUrl" 2^>nul ^| findstr "VigilKioskUrl"'
  ) do set "KIOSK_URL=%%B"
)
if not defined KIOSK_URL set "KIOSK_URL=about:blank"

rem ---- launch ----
"%CHROME_EXE%" ^
  --kiosk ^
  --no-first-run ^
  --no-default-browser-check ^
  --disable-pinch ^
  --disable-features=TranslateUI ^
  --noerrdialogs ^
  --disable-session-crashed-bubble ^
  --disable-infobars ^
  --overscroll-history-navigation=0 ^
  --check-for-update-interval=31536000 ^
  --autoplay-policy=no-user-gesture-required ^
  --user-data-dir="%LOCALAPPDATA%\Vigil-Kiosk\UserData" ^
  --disk-cache-dir="%LOCALAPPDATA%\Vigil-Kiosk\Cache" ^
  "%KIOSK_URL%"

endlocal
exit /b %ERRORLEVEL%
