@echo off
REM ============================================================
REM  PrivacyForge one-click starter (Windows)
REM  Double-click this file. It opens two windows:
REM  the backend (port 8000) and the web app (port 3000).
REM ============================================================

set "ROOT=%~dp0"
if "%PRIVACYFORGE_MASTER_KEY%"=="" set "PRIVACYFORGE_MASTER_KEY=local-dev-key-change-me"
REM Local dev: if an old test vault was locked with a different key, start fresh
REM instead of blocking the workflow. Do NOT set this where the vault holds
REM mappings you cannot lose.
set "PRIVACYFORGE_VAULT_RESET=1"

echo Starting PrivacyForge backend (port 8000)...
start "PrivacyForge Backend" cmd.exe /k "cd /d "%ROOT%backend" && call .venv\Scripts\activate.bat && set PRIVACYFORGE_MASTER_KEY=%PRIVACYFORGE_MASTER_KEY% && set PRIVACYFORGE_VAULT_RESET=1 && uvicorn privacyforge.api:app --host 127.0.0.1 --port 8000"

echo Starting PrivacyForge web app (port 3000)...
start "PrivacyForge Web" cmd.exe /k "cd /d "%ROOT%frontend" && npm run dev"

echo.
echo Two windows are opening. Wait about 15 seconds, then open:
echo     http://localhost:3000
echo.
echo Keep both windows open while you use PrivacyForge.
pause
