@echo off
rem -----------------------------------------------------------------------
rem Vigil-Portable launcher. Roadmap X23.
rem
rem Drop this file next to chrome.exe (in the zip release).
rem
rem Behavior:
rem
rem   1. If a directory called `portable_data\` exists next to this script,
rem      Vigil launches with --user-data-dir set to that directory and the
rem      disk cache routed there. All profile state lives in the same folder
rem      as the executable -- safe to put on a USB stick.
rem
rem   2. If `portable_data\` does NOT exist, the script bails with a message
rem      so the user understands that creating the sentinel directory is
rem      what activates portable mode.
rem
rem Mirrors the Supermium portable-mode convention, see
rem https://github.com/win32ss/supermium for prior art.
rem -----------------------------------------------------------------------

setlocal

set "HERE=%~dp0"
set "CHROME_EXE=%HERE%chrome.exe"
set "PORTABLE_DIR=%HERE%portable_data"

if not exist "%CHROME_EXE%" (
  echo Could not find chrome.exe at %CHROME_EXE%
  echo Place vigil-portable.cmd in the same folder as chrome.exe.
  pause
  exit /b 1
)

if not exist "%PORTABLE_DIR%" (
  echo.
  echo  Vigil portable-mode launcher
  echo  ----------------------------
  echo.
  echo  Portable mode is not yet enabled in this folder.
  echo  To turn it on, create an empty directory called "portable_data"
  echo  next to chrome.exe, then run this script again.
  echo.
  echo      mkdir "%PORTABLE_DIR%"
  echo.
  echo  (Or run this script with --init to create it for you.)
  echo.
  if /I "%~1"=="--init" (
    mkdir "%PORTABLE_DIR%"
    echo  Created %PORTABLE_DIR%. Re-running...
    goto :launch
  )
  pause
  exit /b 0
)

:launch
"%CHROME_EXE%" ^
  --user-data-dir="%PORTABLE_DIR%\UserData" ^
  --disk-cache-dir="%PORTABLE_DIR%\Cache" ^
  --no-first-run ^
  --no-default-browser-check ^
  %*

endlocal
exit /b %ERRORLEVEL%
