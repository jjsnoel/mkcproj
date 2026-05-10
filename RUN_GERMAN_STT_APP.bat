@echo off
chcp 65001 > nul
title Munich German STT App

set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"
set "MUNICH_TOOLKIT_ROOT=%ROOT%"
cd /d "%ROOT%apps\german_stt_local"

if not exist "%VENV%\Scripts\python.exe" (
    echo [ERROR] .venv not found. Run RUN_MUNICH_TOOLKIT.bat or SETUP_VIDEO_STT_ONCE.bat first.
    pause
    exit /b 1
)

"%VENV%\Scripts\python.exe" -m streamlit run app.py
pause
