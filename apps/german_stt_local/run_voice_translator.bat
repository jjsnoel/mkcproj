@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Munich Voice Translator - Run

echo ==========================================
echo  Munich Voice Translator Run
echo ==========================================
echo 현재 폴더:
echo %cd%
echo.

if not exist "app.py" (
    echo [오류] app.py가 현재 폴더에 없습니다.
    echo 압축파일 내용물을 german_stt_local 폴더 안에 제대로 풀었는지 확인하세요.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
    echo [오류] .venv가 없습니다.
    echo 먼저 setup_voice_translator_once.bat 을 실행하세요.
    pause
    exit /b 1
)

echo 가상환경 활성화...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [오류] 가상환경 활성화 실패.
    pause
    exit /b 1
)

echo.
echo Streamlit 실행...
echo 브라우저가 안 열리면 주소창에 http://localhost:8502 을 입력하세요.
echo.
python -m streamlit run app.py --server.port 8502 --server.headless false --browser.gatherUsageStats false

echo.
echo Streamlit이 종료되었습니다.
pause
