@echo off
setlocal
chcp 65001 >nul
set "TCM_RUNTIME=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies"
set "TCM_NODE=%TCM_RUNTIME%\node\bin\node.exe"
if exist "%TCM_NODE%" goto node_ready
set "TCM_NODE="
for %%N in (node.exe) do set "TCM_NODE=%%~$PATH:N"
if not defined TCM_NODE goto node_missing
:node_ready
for %%N in ("%TCM_NODE%") do set "PATH=%%~dpN;%PATH%"
cd /d "%~dp0frontend"
if errorlevel 1 goto project_missing
if not exist "package.json" goto project_missing
if exist "node_modules\next\dist\bin\next" goto dependencies_ready
echo Installing project dependencies...
if exist "%TCM_RUNTIME%\bin\fallback\pnpm.cmd" goto bundled_install
where pnpm.cmd >nul 2>nul
if not errorlevel 1 goto pnpm_install
where npm.cmd >nul 2>nul
if errorlevel 1 goto manager_missing
call npm.cmd install --package-lock=false
goto install_done
:pnpm_install
call pnpm.cmd install --frozen-lockfile
goto install_done
:bundled_install
call "%TCM_RUNTIME%\bin\fallback\pnpm.cmd" install --frozen-lockfile
:install_done
if errorlevel 1 goto failed
if not exist "node_modules\next\dist\bin\next" goto failed
:dependencies_ready
if /i "%~1"=="--check" goto check
"%TCM_NODE%" -e "fetch('http://127.0.0.1:3000/',{signal:AbortSignal.timeout(5000)}).then(r=>r.text()).then(t=>process.exit(t.includes('\u672c\u8349\u77e5\u95ee')?0:2)).catch(e=>process.exit(e.name==='TimeoutError'?2:1))"
set "TCM_PROBE=%ERRORLEVEL%"
if "%TCM_PROBE%"=="0" goto already_running
if "%TCM_PROBE%"=="2" goto port_busy
echo Starting frontend. Keep this terminal open.
echo Open http://127.0.0.1:3000/
"%TCM_NODE%" "node_modules\next\dist\bin\next" dev --hostname 127.0.0.1 --port 3000
if errorlevel 1 goto failed
exit /b 0
:already_running
echo Frontend is already running.
echo Open http://127.0.0.1:3000/
exit /b 0
:check
"%TCM_NODE%" --version
"%TCM_NODE%" -p "'Next.js ' + require('./node_modules/next/package.json').version"
echo Launcher check passed.
exit /b 0
:node_missing
echo Node.js was not found. Install Node.js 20.9 or later, then restart VS Code.
goto failed
:project_missing
echo Cannot find frontend\package.json. Keep this launcher in the project root.
goto failed
:manager_missing
echo Dependencies are missing. Install pnpm or npm, then run this launcher again.
goto failed
:port_busy
echo Port 3000 is occupied. Check http://127.0.0.1:3000/ or stop the other server.
exit /b 1
:failed
echo Startup failed. Copy the error above for troubleshooting.
pause
exit /b 1
