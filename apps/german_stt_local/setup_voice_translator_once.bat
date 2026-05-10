@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Munich Voice Translator - Setup

echo ==========================================
echo  Munich Voice Translator Setup
echo ==========================================
echo 현재 폴더:
echo %cd%
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=python"
    goto found_python
)

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3.11"
    goto found_python
)

echo [오류] python 또는 py 명령을 찾지 못했습니다.
echo Python 3.11 설치가 필요합니다.
echo.
pause
exit /b 1

:found_python
echo 사용할 Python 명령:
echo %PYTHON_CMD%
echo.

if not exist ".venv\Scripts\python.exe" (
    echo .venv가 없어서 새로 만듭니다...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo.
        echo [오류] 가상환경 생성 실패.
        echo Python 3.11이 설치되어 있는지 확인하세요.
        pause
        exit /b 1
    )
) else (
    echo 기존 .venv를 사용합니다.
)

echo.
echo 가상환경 활성화...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo.
    echo [오류] .venv 활성화 실패.
    pause
    exit /b 1
)

echo.
echo Python 버전 확인:
python --version

echo.
echo pip 업데이트...
python -m pip install --upgrade pip

echo.
echo 패키지 설치 시작...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [오류] requirements 설치 실패.
    echo 위쪽 빨간 에러 부분을 캡처해서 보내주세요.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo 설치 완료!
echo 이제 run_voice_translator.bat 을 더블클릭하세요.
echo ==========================================
pause
