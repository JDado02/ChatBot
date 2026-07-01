# PROGRESS — AI Concierge

**Ultimo aggiornamento:** 2026-07-01
**Fase attuale:** Passi 1–2 verificati; Passo 3 scritto e validato. In corso: Passo 4.

> Segnalibro del progetto. Per riprendere una sessione: **`git pull`**, poi leggi questo file, l'ultimo commit e il report più recente in `docs/`.

## Stato in breve

- **Ambiente Docker**: PostgreSQL 16 + pgvector, Redis 7 (`docker-compose.yml`).
- **Schema DB** con 3 tabelle + **RLS multi-tenant** (`db/init/01_schema.sql`), ruolo non-superuser `app_user`, `ALTER DEFAULT PRIVILEGES` per tabelle future.
- **Seed ricco** (`db/init/02_seed.sql`): `hotel_alpha` con **30 stanze** (JSONB completo incl. `view_and_exposure`) + **14 schede** knowledge base; `hotel_beta` piccolo per il contrasto multi-tenant.
- **Test isolamento RLS**: 4/4 PASS (verificato sull'altro PC — vedi [docs/01](docs/01_setup_docker_database.md)).
- Validazione statica del seed: apici bilanciati + grammatica Postgres reale (`pglast`). Vedi [docs/02](docs/02_seed_dati_test.md).

## ⚠️ Da fare al prossimo avvio con Docker

Il seed nuovo (30 stanze) **non è ancora caricato**: gli script `db/init/` girano solo su volume vuoto. Per caricarlo:
```
docker compose down -v && docker compose up -d && ./db/test/run_isolation_test.sh
```
(Su questa macchina Docker Desktop non era avviabile: WSL2 senza distribuzioni. Verifica runtime rimandata.)

## Roadmap (sez. 14 del documento di architettura)

- [x] **1.** Ambiente locale Docker Compose: PostgreSQL + pgvector + Redis
- [x] **2.** RLS sulle tabelle + test isolamento — ✅ verificato (4/4 PASS)
- [x] **3.** Dati di test: 30 stanze (JSONB) + knowledge base — scritto+validato, da caricare (`down -v`)
- [ ] **4.** Pipeline di embedding (modello locale) + ricerca semantica con pgvector  ← IN CORSO
- [ ] **5.** Sicurezza widget: allowlist domini + rate limiting + token di sessione
- [ ] **6.** Endpoint FastAPI: chat, sessioni Redis, RAG sulla knowledge base, lettura stanze
- [ ] **7.** System prompt: regole di risposta + dati/calcoli deterministici (prezzi, orari, conversioni)
- [ ] **8.** Function calling: richiesta prenotazione (email reception) + adapter PMS del primo hotel
- [ ] **9.** Server GPU dedicato EU (noleggio iniziale) con vLLM

## Prossimo passo

**Passo 4:** pipeline di **embedding** (modello locale — bge-m3 / multilingual-e5, dim 1024 — via Ollama in dev) per popolare `knowledge_base.embedding`, e **ricerca semantica** con pgvector (coseno, indice HNSW) per il RAG. Prima base di codice Python del backend.

## Decisioni prese

- **2026-07-01** — Flusso a **singolo agente**, "autonomia a blocchi", no multi-agente. Motivo: budget token (Pro) + coerenza sui vincoli trasversali. Stato in `PROGRESS.md` + commit piccoli.
- **2026-07-01** — Integrato con rebase il lavoro pre-esistente dal remoto (Passi 1–2). Ruoli file: `CLAUDE.md`=regole, `PROGRESS.md`=stato, `README.md`=panoramica, `docs/`=architettura + report per-passo.
- **2026-07-01** — Passo 3: seed generato via `CROSS JOIN` (6 archetipi × 5 piani = 30 stanze) invece di 30 INSERT a mano; `view_and_exposure` derivato dal piano. Aggiunto `ALTER DEFAULT PRIVILEGES` in `01_schema.sql`.
- **2026-06-18** (dal remoto) — Ruolo `app_user` non-superuser; `FORCE ROW LEVEL SECURITY`; policy `SET LOCAL` + `current_setting(..., true)` fail-safe. Dettagli in [docs/01](docs/01_setup_docker_database.md).

## Note / questioni aperte

- **Docker su questa macchina**: backend WSL2 non avviabile senza installare una distro (modifica di sistema non fatta in autonomia). Verifiche runtime rimandate al prossimo avvio Docker.
- Convenzione: a ogni passo aggiornare `PROGRESS.md` + `README.md` e scrivere un report in `docs/0N_*.md`.
