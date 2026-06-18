#!/bin/bash
# =============================================================================
# 00_create_app_role.sh
# Crea il ruolo applicativo NON-superuser PRIMA dello schema (ordine alfabetico).
#
# Gli script .sql di init non possono leggere le variabili d'ambiente del
# sistema operativo; uno script .sh sì. Per questo la creazione del ruolo
# (che richiede la password da env) sta qui, mentre tabelle/RLS/grant stanno
# in 01_schema.sql.
#
# Il nome del ruolo è fisso: "app_user". Solo la password è configurabile
# tramite la variabile d'ambiente APP_DB_PASSWORD (vedi docker-compose.yml).
# =============================================================================
set -euo pipefail

APP_DB_PASSWORD="${APP_DB_PASSWORD:-app_dev_only}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
      CREATE ROLE app_user LOGIN PASSWORD '${APP_DB_PASSWORD}';
    END IF;
  END
  \$\$;
SQL

echo "[init] Ruolo 'app_user' pronto."
