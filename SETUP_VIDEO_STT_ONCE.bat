@echo off
chcp 65001 > nul
title Setup German STT Requirements

set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"
cd /d "%ROOT%"

echo ==========================================
echo  Setup video STT / translation packages
echo ==========================================
echo This may take a long time on first run.
echo.

if not exist "%VENV%\Scripts\python.exe" (
    echo [SETUP] Creating virtual environment...
    py -3.11 -m venv "%VENV%" 2>nul
    if errorlevel 1 py -m venv "%VENV%" 2>nul
    if errorlevel 1 python -m venv "%VENV%"
)

"%VENV%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV%\Scripts\python.exe" -m pip install -r "%ROOT%requirements_video_stt.txt"

echo.
echo Done. Now run RUN_MUNICH_TOOLKIT.bat and open the German subtitle page.
echo If you want GPU CUDA torch, install the CUDA build of PyTorch separately from pytorch.org.
pause
