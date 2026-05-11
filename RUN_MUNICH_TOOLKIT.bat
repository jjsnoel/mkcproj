@echo off
chcp 65001 > nul
title Munich Unified Toolkit

set "ROOT=%~dp0"
set "APP_DIR=%ROOT%apps\instagram_dashboard"
set "VENV=%ROOT%.venv"
set "MUNICH_TOOLKIT_ROOT=%ROOT%"
set "BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
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
    if errorlevel 1 if exist "%BUNDLED_PYTHON%" "%BUNDLED_PYTHON%" -m venv "%VENV%"
)

if exist "%VENV%\Scripts\python.exe" (
    "%VENV%\Scripts\python.exe" --version >nul 2>nul
    if errorlevel 1 (
        echo [SETUP] Repairing virtual environment...
        py -3.11 -m venv "%VENV%" 2>nul
        if errorlevel 1 py -m venv "%VENV%" 2>nul
        if errorlevel 1 python -m venv "%VENV%"
        if errorlevel 1 if exist "%BUNDLED_PYTHON%" "%BUNDLED_PYTHON%" -m venv "%VENV%"
    )
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
