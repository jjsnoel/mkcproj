@echo off
title Munich Boys Choir Admin Dashboard

cd /d "%~dp0"

echo ==========================================
echo  Munich Boys Choir Admin Dashboard
echo ==========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv 가상환경을 찾을 수 없습니다.
    echo 먼저 VS Code 터미널에서 py -m venv .venv 를 실행해야 합니다.
    pause
    exit /b
)

if not exist "app.py" (
    echo [ERROR] app.py 파일을 찾을 수 없습니다.
    pause
    exit /b
)

call ".venv\Scripts\activate.bat"

echo 대시보드를 실행합니다...
echo 브라우저가 자동으로 열리지 않으면 아래 주소로 들어가세요.
echo http://localhost:8501
echo.

python -m streamlit run app.py

pause