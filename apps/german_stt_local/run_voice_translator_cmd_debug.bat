@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Munich Voice Translator - Debug Run

echo 디버그 실행입니다. 창이 바로 꺼지지 않습니다.
echo 현재 폴더: %cd%
echo.

echo 파일 목록:
dir /b
echo.

echo Python 위치:
where python
echo.

echo py 위치:
where py
echo.

echo .venv 확인:
dir ".venv\Scripts" 2>nul
echo.

pause

call ".venv\Scripts\activate.bat"
python --version
python -m streamlit run app.py

pause
