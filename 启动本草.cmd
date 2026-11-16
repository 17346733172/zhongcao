@echo off
setlocal
chcp 65001 >nul
powershell.exe -NoProfile -File "%~dp0scripts\start-local.ps1"
set "BENCAO_EXIT=%ERRORLEVEL%"
echo.
echo Closing this window does not stop the background services.
pause
exit /b %BENCAO_EXIT%
