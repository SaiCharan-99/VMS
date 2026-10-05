# One-command local setup for Windows (PowerShell).
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
# Creates .env with random secrets (if missing), builds and starts the Docker stack, and creates
# demo logins. Safe to re-run: an existing .env and existing users are kept.
param(
    [switch]$NoDemo,      # skip the demo logins
    [switch]$NoML         # small image without EasyOCR/YOLO (faster build, weaker analysis)
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Fail($msg) { Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }
function NewSecret([int]$bytes) {
    $b = New-Object byte[] $bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
    return ([Convert]::ToBase64String($b) -replace '[+/=]', '')
}
function PortFree([int]$port) {
    -not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}
function FirstFreePort([int[]]$ports) {
    foreach ($p in $ports) { if (PortFree $p) { return $p } }
    Fail "None of the ports $($ports -join ', ') is free."
}
function SetEnvValue([string]$key, [string]$value) {
    $lines = Get-Content .env
    if ($lines -match "^$key=") { $lines = $lines -replace "^$key=.*", "$key=$value" }
    else { $lines += "$key=$value" }
    [IO.File]::WriteAllLines("$PWD\.env", $lines)   # UTF-8 without BOM
}

Step "Checking Docker"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail "Docker is not installed. Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
}
docker info *> $null
if ($LASTEXITCODE -ne 0) { Fail "Docker is installed but not running. Start Docker Desktop and re-run." }

Step "Preparing .env"
if (Test-Path .env) {
    Write-Host ".env already exists: keeping it."
} else {
    Copy-Item .env.example .env
    SetEnvValue "VMS_JWT_SECRET" (NewSecret 48)
    SetEnvValue "POSTGRES_PASSWORD" (NewSecret 24)
    SetEnvValue "VMS_HTTP_PORT" (FirstFreePort @(80, 8080, 8081, 8888))
    SetEnvValue "VMS_API_PORT" (FirstFreePort @(8000, 18000, 18001))
    SetEnvValue "VMS_PG_PORT" (FirstFreePort @(5432, 55432, 55433))
    Write-Host "Created .env with random secrets."
}
if ($NoML) { SetEnvValue "WITH_ML" "0" }
$httpPort = ((Get-Content .env) -match '^VMS_HTTP_PORT=' | Select-Object -First 1) -replace '^VMS_HTTP_PORT=', ''
if (-not $httpPort) { $httpPort = "80" }

Step "Building and starting the stack (first run downloads ML libraries: 5-15 min)"
docker compose up -d --build --wait
if ($LASTEXITCODE -ne 0) { docker compose logs --tail 50; Fail "The stack did not become healthy (logs above)." }

if (-not $NoDemo) {
    Step "Creating demo logins"
    docker compose exec -T api python -m vms.cli seed-demo
}

$url = if ($httpPort -eq "80") { "http://localhost" } else { "http://localhost:$httpPort" }
Write-Host "`nVMS SOP Analyzer is running at $url" -ForegroundColor Green
Write-Host "API docs: $url/docs    Stop: docker compose down    Logs: docker compose logs -f"
