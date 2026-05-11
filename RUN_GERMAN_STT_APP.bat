@echo off
chcp 65001 > nul
title Munich German STT App

set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"
set "MUNICH_TOOLKIT_ROOT=%ROOT%"
set "CUDA_VISIBLE_DEVICES=0"

if exist "%ROOT%.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT%.env") do (
        if /i "%%A"=="OPENAI_API_KEY" if not "%%B"=="" set "OPENAI_API_KEY=%%B"
        if /i "%%A"=="OPENAI_STT_MODEL" if not "%%B"=="" set "OPENAI_STT_MODEL=%%B"
        if /i "%%A"=="LOCAL_WHISPER_MODEL" if not "%%B"=="" set "LOCAL_WHISPER_MODEL=%%B"
        if /i "%%A"=="OPENAI_STT_CHUNK_SECONDS" if not "%%B"=="" set "OPENAI_STT_CHUNK_SECONDS=%%B"
        if /i "%%A"=="DEEPL_API_KEY" if not "%%B"=="" set "DEEPL_API_KEY=%%B"
        if /i "%%A"=="DEEPL_AUTH_KEY" if not defined DEEPL_API_KEY if not "%%B"=="" set "DEEPL_API_KEY=%%B"
        if /i "%%A"=="DEEPL_API_PLAN" if not "%%B"=="" set "DEEPL_API_PLAN=%%B"
        if /i "%%A"=="DEEPL_API_URL" if not "%%B"=="" set "DEEPL_API_URL=%%B"
    )
)
for /f "usebackq delims=" %%K in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('OPENAI_API_KEY','User')"`) do if not "%%K"=="" set "OPENAI_API_KEY=%%K"
for /f "usebackq delims=" %%M in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('OPENAI_STT_MODEL','User')"`) do if not "%%M"=="" set "OPENAI_STT_MODEL=%%M"
for /f "usebackq delims=" %%M in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('LOCAL_WHISPER_MODEL','User')"`) do if not "%%M"=="" set "LOCAL_WHISPER_MODEL=%%M"
for /f "usebackq delims=" %%S in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('OPENAI_STT_CHUNK_SECONDS','User')"`) do if not "%%S"=="" set "OPENAI_STT_CHUNK_SECONDS=%%S"
for /f "usebackq delims=" %%K in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('DEEPL_API_KEY','User')"`) do if not "%%K"=="" set "DEEPL_API_KEY=%%K"
if not defined DEEPL_API_KEY (
    for /f "usebackq delims=" %%K in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('DEEPL_AUTH_KEY','User')"`) do if not "%%K"=="" set "DEEPL_API_KEY=%%K"
)
for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('DEEPL_API_PLAN','User')"`) do if not "%%P"=="" set "DEEPL_API_PLAN=%%P"
if defined DEEPL_API_KEY if not defined DEEPL_API_PLAN set "DEEPL_API_PLAN=free"

cd /d "%ROOT%apps\german_stt_local"

if not exist "%VENV%\Scripts\python.exe" (
    echo [ERROR] .venv not found. Run RUN_MUNICH_TOOLKIT.bat or SETUP_VIDEO_STT_ONCE.bat first.
    pause
    exit /b 1
)

echo German STT app will open at http://localhost:8502
"%VENV%\Scripts\python.exe" -m streamlit run app.py --server.port 8502 --server.headless false --browser.gatherUsageStats false
pause
