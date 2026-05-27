@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM start_backend.bat — Inicia o backend (API + frontend em http://localhost:8000)
REM Node.js NÃO é necessário — o FastAPI serve o frontend já compilado.
REM
REM Para acessar pelo IP da rede, descomente e ajuste a linha ALLOWED_ORIGINS.
REM ─────────────────────────────────────────────────────────────────────────────

title Speed Detection

cd /d "%~dp0"

call venv\Scripts\activate.bat

REM set ALLOWED_ORIGINS=http://SEU_IP:8000

echo Iniciando em http://localhost:8000 ...
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1

pause
