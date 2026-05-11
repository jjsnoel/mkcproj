@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "ROOT=%~dp0"
set "ENV_FILE=%ROOT%.env"

echo.
echo Paste your OpenAI API key. It will be saved to:
echo %ENV_FILE%
echo.
set /p "OPENAI_KEY=OPENAI_API_KEY: "

if "%OPENAI_KEY%"=="" (
    echo [ERROR] Empty key. Nothing was changed.
    exit /b 1
)

if not exist "%ENV_FILE%" (
    type nul > "%ENV_FILE%"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$path = '%ENV_FILE%';" ^
  "$key = [Environment]::GetEnvironmentVariable('OPENAI_KEY', 'Process');" ^
  "$lines = if (Test-Path $path) { Get-Content -LiteralPath $path } else { @() };" ^
  "$found = $false;" ^
  "$updated = foreach ($line in $lines) { if ($line -match '^OPENAI_API_KEY=') { $found = $true; 'OPENAI_API_KEY=' + $key } else { $line } };" ^
  "if (-not $found) { $updated += 'OPENAI_API_KEY=' + $key };" ^
  "if (-not ($updated -match '^OPENAI_STT_MODEL=')) { $updated += 'OPENAI_STT_MODEL=gpt-4o-transcribe' };" ^
  "if (-not ($updated -match '^LOCAL_WHISPER_MODEL=')) { $updated += 'LOCAL_WHISPER_MODEL=large-v3' };" ^
  "if (-not ($updated -match '^OPENAI_STT_CHUNK_SECONDS=')) { $updated += 'OPENAI_STT_CHUNK_SECONDS=600' };" ^
  "[System.IO.File]::WriteAllLines($path, $updated, [System.Text.UTF8Encoding]::new($false))"

if errorlevel 1 (
    echo [ERROR] Failed to update .env.
    exit /b 1
)

echo [OK] OpenAI API key saved.
echo Restart the Munich toolkit app so it reloads .env.
