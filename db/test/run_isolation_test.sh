#!/bin/bash
# =============================================================================
# run_isolation_test.sh
# Esegue il test di isolamento RLS connettendosi come 'app_user' (NON superuser)
# dentro il container Postgres. Carica le variabili da .env.
#
# Uso:  ./db/test/run_isolation_test.sh
# Prerequisito: i container sono su ( docker compose up -d ).
# =============================================================================
set -euo pipefail

# Cartella radice del progetto (due livelli sopra questo script)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# Carica .env se presente
if [ -f .env ]; then
  set -a; source .env; set +a
fi

APP_DB_PASSWORD="${APP_DB_PASSWORD:-app_dev_only}"
POSTGRES_DB="${POSTGRES_DB:-concierge}"

echo "[test] Eseguo il test di isolamento come ruolo 'app_user'..."
docker compose exec -T -e PGPASSWORD="$APP_DB_PASSWORD" postgres \
  psql -v ON_ERROR_STOP=1 -U app_user -d "$POSTGRES_DB" \
  < db/test/test_rls_isolation.sql

echo "[test] Completato."
