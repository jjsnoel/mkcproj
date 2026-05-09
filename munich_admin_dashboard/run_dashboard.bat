@echo off
title Munich Boys Choir Admin Dashboard
cd /d "%~dp0"

echo ==========================================
echo Munich Boys Choir Admin Dashboard
echo ==========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python launcher was not found.
    echo Please install Python and check Add python.exe to PATH.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [SETUP] Creating virtual environment...
    py -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo [SETUP] Upgrading pip...
python -m pip install --upgrade pip

echo [SETUP] Installing requirements...
python -m pip install -r requirements.txt

if not exist "app.py" (
    echo [ERROR] app.py was not found.
    pause
    exit /b 1
)

echo.
echo Starting dashboard...
echo If browser does not open, go to:
echo http://localhost:8501
echo.

python -m streamlit run app.py

pause
