# ──────────────────────────────────────────────────────────────────────────────
# setup_windows.ps1
# Setup completo do Speed Detection Dashboard
# Windows Server 2022 + NVIDIA GeForce RTX 4060 (CUDA 12.4)
#
# Execute como Administrador no PowerShell:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\setup_windows.ps1
# ──────────────────────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"

Write-Host "=== Speed Detection Dashboard — Setup Windows ===" -ForegroundColor Cyan

# ── 1. Verificar Python ──────────────────────────────────────────────────────
Write-Host "`n[1/7] Verificando Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python nao encontrado. Instale Python 3.11 ou 3.12 em https://www.python.org/downloads/"
    exit 1
}
Write-Host "  $pythonVersion" -ForegroundColor Green

# ── 2. Verificar GPU NVIDIA ──────────────────────────────────────────────────
Write-Host "`n[2/7] Verificando GPU NVIDIA..." -ForegroundColor Yellow
$nvidiaSmi = & "nvidia-smi" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "nvidia-smi nao encontrado. Instale os drivers NVIDIA (>= 551.x)."
    exit 1
}
Write-Host "  GPU detectada:" -ForegroundColor Green
$nvidiaSmi | Select-String "GeForce|RTX|GTX|Quadro|Tesla" | ForEach-Object { Write-Host "  $_" -ForegroundColor Green }

# ── 3. Criar ambiente virtual ────────────────────────────────────────────────
Write-Host "`n[3/7] Criando ambiente virtual Python..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "  venv/ criado." -ForegroundColor Green
} else {
    Write-Host "  venv/ ja existe, pulando." -ForegroundColor DarkGray
}

# Ativar venv
& ".\venv\Scripts\Activate.ps1"

# ── 4. Instalar PyTorch com CUDA 12.4 ───────────────────────────────────────
Write-Host "`n[4/7] Instalando PyTorch + CUDA 12.4..." -ForegroundColor Yellow
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Error "Falha ao instalar PyTorch."
    exit 1
}
Write-Host "  PyTorch CUDA instalado." -ForegroundColor Green

# ── 5. Instalar demais dependências ─────────────────────────────────────────
Write-Host "`n[5/7] Instalando dependencias do projeto..." -ForegroundColor Yellow
pip install -r requirements-windows-cuda.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Error "Falha ao instalar dependencias."
    exit 1
}
Write-Host "  Dependencias instaladas." -ForegroundColor Green

# ── 6. Validar CUDA no PyTorch ───────────────────────────────────────────────
Write-Host "`n[6/7] Validando CUDA no PyTorch..." -ForegroundColor Yellow
$cudaTest = python -c "import torch; print(f'CUDA disponivel: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')" 2>&1
Write-Host "  $cudaTest" -ForegroundColor Green

# ── 7. Exportar modelo para TensorRT ────────────────────────────────────────
Write-Host "`n[7/7] Exportando modelo YOLO para TensorRT FP16..." -ForegroundColor Yellow
if (Test-Path "yolo11n.engine") {
    Write-Host "  yolo11n.engine ja existe, pulando exportacao." -ForegroundColor DarkGray
    Write-Host "  (delete yolo11n.engine e rode novamente se precisar reexportar)" -ForegroundColor DarkGray
} else {
    Write-Host "  Isso pode levar 3-5 minutos na primeira vez..." -ForegroundColor DarkCyan
    python export_tensorrt.py
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Exportacao TensorRT falhou. O backend usara yolo11n.pt como fallback (mais lento)."
    } else {
        Write-Host "  yolo11n.engine gerado com sucesso." -ForegroundColor Green
    }
}

# ── 8. Instalar dependencias do frontend ────────────────────────────────────
Write-Host "`n[+] Instalando dependencias do frontend (Node.js)..." -ForegroundColor Yellow
if (-not (Get-Command "npm" -ErrorAction SilentlyContinue)) {
    Write-Warning "npm nao encontrado. Instale Node.js >= 20 em https://nodejs.org/"
} else {
    Push-Location frontend
    npm install --silent
    Pop-Location
    Write-Host "  Frontend pronto." -ForegroundColor Green
}

Write-Host "`n=== Setup concluido! ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Proximos passos:" -ForegroundColor White
Write-Host "  1. Edite backend\config.py e ajuste RTSP_URL, ROI_Y_MIN, ROI_Y_MAX e METERS_PER_PIXEL"
Write-Host "  2. Inicie o sistema:"
Write-Host "       .\start_backend.bat    (terminal 1)"
Write-Host "       .\start_frontend.bat   (terminal 2)"
Write-Host "  3. Acesse http://localhost:5173"
Write-Host ""
