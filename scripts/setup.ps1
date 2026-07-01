# =============================================================================
# setup.ps1 - installa e avvia l'ambiente AI Concierge (Windows PowerShell)
#
# Uso:
#   .\scripts\setup.ps1                 # DB + Redis + test + dipendenze backend
#   .\scripts\setup.ps1 -WithOllama     # anche: scarica i modelli e genera embedding
#
# Prerequisiti: Docker Desktop, Python 3.11+, Git (per bash), (opz.) Ollama.
# Se l'esecuzione script e' bloccata:  powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
# =============================================================================
param([switch]$WithOllama)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

function Say($m) { Write-Host "`n== $m ==" -ForegroundColor Cyan }

# 0) Prerequisiti
Say "Controllo prerequisiti"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Write-Host "Docker non trovato. Installa Docker Desktop: https://docker.com"; exit 1 }
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $py) { Write-Host "Python non trovato (serve 3.11+)."; exit 1 }
$PY = $py.Source
Write-Host "Docker OK - Python: $(& $PY --version)"

# 1) Config locale
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Creato .env dal template" } else { Write-Host ".env gia' presente" }

# 2) Container
Say "Avvio container (PostgreSQL + pgvector, Redis)"
docker compose up -d
Write-Host -NoNewline "Attendo Postgres 'healthy'"
for ($i = 0; $i -lt 40; $i++) {
  $s = docker inspect --format '{{.State.Health.Status}}' concierge_postgres 2>$null
  if ($s -eq "healthy") { Write-Host " OK"; break }
  Write-Host -NoNewline "."; Start-Sleep -Seconds 2
}

# 3) Test isolamento RLS (serve bash, incluso in Git per Windows)
Say "Test isolamento multi-tenant (RLS)"
if (Get-Command bash -ErrorAction SilentlyContinue) {
  bash db/test/run_isolation_test.sh
} else {
  Write-Host "bash non trovato: salto il test isolamento (installa Git per Windows)."
}

# 4) Backend: dipendenze + test
Say "Backend: dipendenze ed esecuzione test"
& $PY -m pip install -r backend/requirements.txt
Push-Location backend
& $PY -m pytest -q
Pop-Location

# 5) Ollama (opzionale)
if ($WithOllama) {
  Say "Ollama: modelli + embedding"
  if (Get-Command ollama -ErrorAction SilentlyContinue) {
    ollama pull bge-m3
    ollama pull llama3
    Push-Location backend
    & $PY scripts/generate_embeddings.py hotel_alpha hotel_beta
    Pop-Location
  } else {
    Write-Host "Ollama non installato. Installalo da https://ollama.com, poi: ollama pull bge-m3; ollama pull llama3"
  }
}

# 6) Fatto
Say "Setup completato - prossimi passi"
Write-Host "  API:    cd backend; uvicorn app.api.main:app --reload   # http://localhost:8000/docs"
Write-Host "  Widget: python -m http.server 5500 --directory widget   # http://localhost:5500"
