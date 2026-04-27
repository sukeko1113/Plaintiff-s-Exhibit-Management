@echo off
setlocal
cd /d "%~dp0"

REM ---------- detect Python ----------
set "PYTHON_CMD="
where py
if not errorlevel 1 (
  set "PYTHON_CMD=py -3"
  goto :py_found
)
where python
if not errorlevel 1 (
  set "PYTHON_CMD=python"
  goto :py_found
)
echo.
echo [ERROR] Python not found in PATH.
echo  Install Python 3.10+ from https://www.python.org/downloads/
echo  and tick "Add python.exe to PATH" during installation.
echo.
pause
exit /b 1
:py_found
echo [INFO] Python: %PYTHON_CMD%

REM ---------- create venv on first run ----------
if not exist ".venv\Scripts\python.exe" (
  echo [SETUP] Creating virtual environment...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 (
    echo.
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
  )
)

REM ---------- install dependencies ----------
echo [INFO] Checking dependencies...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo.
  echo [ERROR] Failed to install dependencies.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo  Kogo Kanri System is starting up
echo  Open http://127.0.0.1:8000/ in your browser
echo  Press Ctrl+C to stop
echo ============================================================
echo.

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

echo.
echo Server exited (exit code = %errorlevel%).
pause
endlocal
