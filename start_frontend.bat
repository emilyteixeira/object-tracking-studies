@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM start_frontend.bat — Inicia o frontend Vite em modo dev
REM ─────────────────────────────────────────────────────────────────────────────

title Speed Detection — Frontend

cd /d "%~dp0\frontend"

echo Iniciando frontend (porta 5173)...
npm run dev

pause
