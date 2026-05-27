# ──────────────────────────────────────────────────────────────────────────────
# install_service_windows.ps1
# Registra o backend como Windows Service usando NSSM
# (Non-Sucking Service Manager) — https://nssm.cc/download
#
# Execute como Administrador:
#   .\install_service_windows.ps1
# ──────────────────────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"

$ServiceName  = "SpeedDetectionBackend"
$ProjectRoot  = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe    = "$ProjectRoot\venv\Scripts\python.exe"
$NssmExe      = "nssm"   # assume nssm.exe no PATH; ajuste se necessário

Write-Host "=== Instalando Windows Service: $ServiceName ===" -ForegroundColor Cyan

# Verificar NSSM
if (-not (Get-Command $NssmExe -ErrorAction SilentlyContinue)) {
    Write-Error @"
NSSM nao encontrado no PATH.
Baixe em https://nssm.cc/download, extraia nssm.exe e adicione ao PATH do sistema,
ou coloque nssm.exe na pasta do projeto e altere a variavel NssmExe neste script.
"@
    exit 1
}

# Remover servico existente (se houver)
$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removendo servico existente..." -ForegroundColor Yellow
    & $NssmExe remove $ServiceName confirm
}

# Registrar servico
Write-Host "Registrando servico..." -ForegroundColor Yellow
& $NssmExe install $ServiceName $PythonExe "-m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

# Configurar diretório de trabalho
& $NssmExe set $ServiceName AppDirectory $ProjectRoot

# Redirecionar stdout/stderr para arquivos de log
$LogDir = "$ProjectRoot\logs"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
& $NssmExe set $ServiceName AppStdout "$LogDir\backend_stdout.log"
& $NssmExe set $ServiceName AppStderr "$LogDir\backend_stderr.log"
& $NssmExe set $ServiceName AppRotateFiles 1
& $NssmExe set $ServiceName AppRotateBytes 10485760   # 10 MB

# Restart automático em caso de falha
& $NssmExe set $ServiceName AppExit Default Restart
& $NssmExe set $ServiceName AppRestartDelay 5000

# Iniciar servico
Write-Host "Iniciando servico..." -ForegroundColor Yellow
Start-Service -Name $ServiceName
$svc = Get-Service -Name $ServiceName
Write-Host "  Status: $($svc.Status)" -ForegroundColor Green

Write-Host "`n=== Servico instalado! ===" -ForegroundColor Cyan
Write-Host "  Gerenciar: services.msc ou 'nssm edit $ServiceName'"
Write-Host "  Logs:      $LogDir"
Write-Host "  API:       http://localhost:8000"
Write-Host ""
