#!/usr/bin/env bash
# =============================================================================
# setup.sh — installa e avvia tutto l'ambiente AI Concierge (Linux/macOS/Git-Bash)
#
# Uso:
#   ./scripts/setup.sh                 # DB + Redis + test + dipendenze backend
#   ./scripts/setup.sh --with-ollama   # anche: scarica i modelli e genera embedding
#
# Prerequisiti: Docker, Python 3.11+, (opzionale) Ollama.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."   # radice del repo

say() { printf "\n\033[1;36m== %s ==\033[0m\n" "$1"; }

# 0) Prerequisiti -------------------------------------------------------------
say "Controllo prerequisiti"
command -v docker >/dev/null || { echo "Docker non trovato. Installa Docker Desktop: https://docker.com"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "Docker Compose non disponibile."; exit 1; }
PY=$(command -v python3 || command -v python) || { echo "Python non trovato (serve 3.11+)."; exit 1; }
echo "Docker OK · Python: $("$PY" --version)"

# 1) Config locale ------------------------------------------------------------
if [ ! -f .env ]; then cp .env.example .env; echo "Creato .env dal template"; else echo ".env già presente"; fi

# 2) Container ----------------------------------------------------------------
say "Avvio container (PostgreSQL + pgvector, Redis)"
docker compose up -d
printf "Attendo Postgres 'healthy'"
for _ in $(seq 1 40); do
  s=$(docker inspect --format '{{.State.Health.Status}}' concierge_postgres 2>/dev/null || echo "")
  if [ "$s" = "healthy" ]; then printf " OK\n"; break; fi
  printf "."; sleep 2
done

# 3) Test isolamento RLS ------------------------------------------------------
say "Test isolamento multi-tenant (RLS)"
bash db/test/run_isolation_test.sh || echo ">> Test isolamento NON superato: controlla i log di 'docker compose logs postgres'"

# 4) Backend: dipendenze + test ----------------------------------------------
say "Backend: installo dipendenze ed eseguo i test"
"$PY" -m pip install -r backend/requirements.txt
( cd backend && "$PY" -m pytest -q )

# 5) Ollama (opzionale) -------------------------------------------------------
if [ "${1:-}" = "--with-ollama" ]; then
  say "Ollama: modelli + embedding"
  if command -v ollama >/dev/null; then
    ollama pull bge-m3
    ollama pull llama3
    ( cd backend && "$PY" scripts/generate_embeddings.py hotel_alpha hotel_beta )
  else
    echo "Ollama non installato. Installalo da https://ollama.com, poi:"
    echo "   ollama pull bge-m3 && ollama pull llama3"
    echo "   (cd backend && $PY scripts/generate_embeddings.py hotel_alpha hotel_beta)"
  fi
fi

# 6) Fatto --------------------------------------------------------------------
say "Setup completato — prossimi passi"
cat <<EOF
  API:    cd backend && uvicorn app.api.main:app --reload   # http://localhost:8000/docs
  Widget: python -m http.server 5500 --directory widget     # http://localhost:5500
  Test isolamento: ./db/test/run_isolation_test.sh          # atteso 4x PASS
EOF
