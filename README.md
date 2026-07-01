# AI Concierge

Assistente virtuale (chatbot) multi-tenant per hotel e altre attività, self-hosted in Europa (GDPR-first).

Documento di contesto completo: [`docs/AI_Concierge_Contesto_Progetto.md`](docs/AI_Concierge_Contesto_Progetto.md).
Flusso di lavoro e avanzamento: [`CLAUDE.md`](CLAUDE.md) (regole) e [`PROGRESS.md`](PROGRESS.md) (roadmap e stato).

## Stato attuale

Realizzato finora (vedi [`docs/01_setup_docker_database.md`](docs/01_setup_docker_database.md)):

- Ambiente locale con **Docker Compose**: PostgreSQL 16 + pgvector, Redis 7.
- Schema database: tabelle `rooms`, `knowledge_base`, `booking_requests`.
- Multi-tenancy con **Row-Level Security**: ogni hotel vede solo i propri dati.
- Ruolo applicativo non-superuser `app_user` (i superuser bypassano la RLS).
- Dati di test (due hotel fittizi) e test automatico di isolamento.

## Requisiti

- Docker + Docker Compose
- (opzionale) un client SQL / IntelliJ per le query

## Avvio

```bash
# 1. crea la config locale (solo la prima volta)
cp .env.example .env

# 2. avvia i container
docker compose up -d

# 3. verifica che siano "healthy"
docker compose ps
```

Connessioni:

- PostgreSQL → `localhost:5432`, database `concierge`, ruolo backend `app_user`
- Redis → `localhost:6379`

## Test di isolamento

```bash
./db/test/run_isolation_test.sh
```

Esito atteso: 4 righe `PASS` e `== TUTTI I TEST SUPERATI ==`.

## Comandi utili

```bash
docker compose logs postgres   # log
docker compose down            # ferma i container (i dati restano)
docker compose down -v         # ferma e cancella i dati (re-init da zero)
```

> Gli script in `db/init/` girano **solo al primo avvio** (DB vuoto). Se modifichi schema o seed, rigenera con `docker compose down -v && docker compose up -d`.

## Struttura

```
.
├── docker-compose.yml
├── .env.example
├── CLAUDE.md          # regole/flusso per Claude Code (auto-caricato)
├── PROGRESS.md        # stato del progetto e roadmap (il "segnalibro")
├── db/
│   ├── init/   # ruolo app, schema+RLS, dati di test (eseguiti all'avvio)
│   └── test/   # test di isolamento RLS
└── docs/       # documentazione e contesto di progetto
```
