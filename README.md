# AI Concierge

[![backend-tests](https://github.com/JDado02/ChatBot/actions/workflows/backend-tests.yml/badge.svg)](https://github.com/JDado02/ChatBot/actions/workflows/backend-tests.yml)

Assistente virtuale (chatbot) multi-tenant per hotel e altre attività, self-hosted in Europa (GDPR-first).

Documento di contesto completo: [`docs/AI_Concierge_Contesto_Progetto.md`](docs/AI_Concierge_Contesto_Progetto.md).
Flusso di lavoro e avanzamento: [`CLAUDE.md`](CLAUDE.md) (regole) e [`PROGRESS.md`](PROGRESS.md) (roadmap e stato).

## Stato attuale

Realizzato finora (report in [`docs/`](docs/)):

- Ambiente locale con **Docker Compose**: PostgreSQL 16 + pgvector, Redis 7.
- Schema database: tabelle `rooms`, `knowledge_base`, `booking_requests`.
- Multi-tenancy con **Row-Level Security**: ogni hotel vede solo i propri dati.
- Ruolo applicativo non-superuser `app_user` (i superuser bypassano la RLS).
- **Dati di test ricchi**: `hotel_alpha` con 30 stanze (dettagli JSONB) + 14 schede
  di knowledge base; `hotel_beta` piccolo per il contrasto multi-tenant.
- Test automatico di isolamento RLS (atteso: 4× `PASS`).
- **Backend Python** ([`backend/`](backend/README.md)):
  - pipeline di embedding (modello locale via Ollama) + **ricerca semantica**
    con pgvector, isolata per tenant dalla RLS;
  - **sicurezza widget**: allowlist domini, token di sessione firmati, rate
    limiting, lookup del tenant dall'API key (tabella `tenants`);
  - **API FastAPI**: `/api/session` (token), `/api/search` (RAG), `/api/rooms`
    (dati stanza), `/api/chat` (RAG + memoria Redis + LLM) e `/api/booking`
    (richiesta di prenotazione → email reception), con l'intera catena di
    sicurezza. Avvio: `uvicorn app.api.main:app --reload`;
  - **anti-allucinazione**: calcoli deterministici (conversioni °C↔K, notti,
    prezzi) fatti dal backend + system prompt con regole di grounding;
  - adapter per **email** (SMTP/stub) e **PMS** (interfaccia + fake, connettore
    reale su misura per cliente).
  - 98 test offline.

Prossimo: verifica runtime (Docker + Ollama), integrazioni reali (LLM tool-calling,
SMTP, PMS) e infrastruttura (server GPU EU, Passo 9).

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
├── backend/    # codice Python: embedding + ricerca semantica (RAG)
├── db/
│   ├── init/   # ruolo app, schema+RLS, dati di test (eseguiti all'avvio)
│   └── test/   # test di isolamento RLS
└── docs/       # documentazione e contesto di progetto
```
