@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0backend"
if not exist "app\main.py" goto missing
set "BENCAO_PYTHON="
if exist ".venv\Scripts\python.exe" goto ready
for %%P in (python.exe) do set "BENCAO_PYTHON=%%~$PATH:P"
if not defined BENCAO_PYTHON goto python_missing
"%BENCAO_PYTHON%" -m venv .venv
if errorlevel 1 goto failed
:ready
set "BENCAO_PYTHON=%CD%\.venv\Scripts\python.exe"
"%BENCAO_PYTHON%" -c "from importlib.metadata import version; import fastapi,uvicorn,argon2,dotenv; assert version('fastapi') == '0.159.1'; assert version('uvicorn') == '0.54.0'; assert version('argon2-cffi') == '25.1.0'; assert version('python-dotenv') == '1.2.1'" >nul 2>nul
if not errorlevel 1 goto dependencies_ready
"%BENCAO_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto failed
:dependencies_ready
if /i "%~1"=="--check" goto check
"%BENCAO_PYTHON%" -m app.cli ensure-admin
if errorlevel 1 goto failed
"%BENCAO_PYTHON%" -c "import json,urllib.request,sys; r=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)); sys.exit(0 if r.get('service')=='bencao-api' else 1)" >nul 2>nul
if not errorlevel 1 goto already_running
echo Starting backend. Keep this terminal open.
echo API docs: http://127.0.0.1:8000/docs
"%BENCAO_PYTHON%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
if errorlevel 1 goto failed
exit /b 0
:check
"%BENCAO_PYTHON%" --version
"%BENCAO_PYTHON%" -c "import fastapi; print('FastAPI ' + fastapi.__version__)"
echo Backend launcher check passed.
exit /b 0
:already_running
echo Backend is already running on http://127.0.0.1:8000/
exit /b 0
:python_missing
echo Python was not found. Install Python 3.11 or later, then retry.
goto failed
:missing
echo Cannot find backend\app\main.py. Keep this launcher in the project root.
goto failed
:failed
echo Backend startup failed. Copy the error above for troubleshooting.
pause
exit /b 1
