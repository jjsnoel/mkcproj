@echo off
chcp 65001 > nul
title Munich Unified Toolkit

set "ROOT=%~dp0"
set "APP_DIR=%ROOT%apps\instagram_dashboard"
set "VENV=%ROOT%.venv"
set "MUNICH_TOOLKIT_ROOT=%ROOT%"

cd /d "%ROOT%"

echo ==========================================
echo  Munich Unified Toolkit
echo ==========================================
echo  1. Instagram hashtag/admin dashboard
echo  2. Facebook photo archive collector page
echo  3. German STT subtitle/translation page
echo ==========================================
echo.

if not exist "%VENV%\Scripts\python.exe" (
    echo [SETUP] Creating virtual environment...
    py -3.11 -m venv "%VENV%" 2>nul
    if errorlevel 1 py -m venv "%VENV%" 2>nul
    if errorlevel 1 python -m venv "%VENV%"
)

if not exist "%VENV%\Scripts\python.exe" (
    echo [ERROR] Python virtual environment could not be created.
    echo Install Python 3.11 and try again.
    pause
    exit /b 1
)

echo [SETUP] Installing dashboard requirements...
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV%\Scripts\python.exe" -m pip install -r "%ROOT%requirements_dashboard.txt"

echo.
echo [SETUP] Closing any existing Streamlit server on port 8501...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8501" ^| findstr "LISTENING"') do (
    taskkill /PID %%P /F >nul 2>nul
)

echo.
echo Dashboard will open at http://localhost:8501
echo If the browser does not open, copy that address manually.
echo.

cd /d "%APP_DIR%"
"%VENV%\Scripts\python.exe" -m streamlit run app.py --server.port 8501 --server.headless false --browser.gatherUsageStats false

pause
