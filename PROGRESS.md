# PROGRESS — AI Concierge

**Ultimo aggiornamento:** 2026-07-01
**Fase attuale:** Passi 1–2 completati e verificati. Prossimo: Passo 3–4.

> Segnalibro del progetto. Per riprendere una sessione: leggi questo file, poi guarda l'ultimo commit git e il report più recente in `docs/`. Non serve altro.

## Stato in breve

- **Ambiente Docker** attivo: PostgreSQL 16 + pgvector, Redis 7 (`docker-compose.yml`).
- **Schema DB** con le 3 tabelle (`rooms`, `knowledge_base`, `booking_requests`) e **RLS multi-tenant** attiva (`db/init/`).
- Ruolo backend **non-superuser `app_user`** (i superuser bypassano la RLS).
- **Seed minimo** per i test: 2 hotel fittizi (`hotel_alpha`, `hotel_beta`) — NON ancora il seed ricco del Passo 3.
- **Test isolamento RLS**: 4/4 PASS (report in [docs/01_setup_docker_database.md](docs/01_setup_docker_database.md)).
- File di workflow (`CLAUDE.md`, `PROGRESS.md`) + `README.md` in repo.

## Roadmap (sez. 14 del documento di architettura)

- [x] **1.** Ambiente locale Docker Compose: PostgreSQL + pgvector + Redis
- [x] **2.** RLS sulle tabelle + test isolamento tra hotel e sessioni — ✅ verificato (4/4 PASS)
- [ ] **3.** Dati di test: 30 stanze fittizie (con JSONB) + knowledge base d'esempio
- [ ] **4.** Pipeline di embedding (modello locale) + ricerca semantica con pgvector
- [ ] **5.** Sicurezza widget: allowlist domini + rate limiting + token di sessione
- [ ] **6.** Endpoint FastAPI: chat, sessioni Redis, RAG sulla knowledge base, lettura stanze
- [ ] **7.** System prompt: regole di risposta + dati/calcoli deterministici (prezzi, orari, conversioni)
- [ ] **8.** Function calling: richiesta prenotazione (email reception) + adapter PMS del primo hotel
- [ ] **9.** Server GPU dedicato EU (noleggio iniziale) con vLLM

## Prossimo passo

**Passo 3–4:** popolare dati di test ricchi (30 stanze con JSONB + knowledge base d'esempio) e implementare la **pipeline di embedding** (modello locale) con la **ricerca semantica** via pgvector. In attesa del via dell'utente.

## Decisioni prese

- **2026-07-01** — Flusso a **singolo agente**, "autonomia a blocchi" (un passo alla volta), no multi-agente. Motivo: budget token (piano Pro) e coerenza sui vincoli trasversali. Stato tracciato in `PROGRESS.md` + commit piccoli.
- **2026-07-01** — Integrato con rebase il lavoro pre-esistente sul remoto (Passi 1–2, commit `80c4b79`/`7ea9ed8`). Ruoli file chiariti: `CLAUDE.md`=regole, `PROGRESS.md`=stato/roadmap, `README.md`=panoramica pubblica, `docs/`=architettura + report per-passo.
- **2026-06-18** (dal remoto) — Ruolo `app_user` non-superuser per far valere la RLS; `FORCE ROW LEVEL SECURITY`; policy con `SET LOCAL` + `current_setting(..., true)` fail-safe. Dettagli in [docs/01_setup_docker_database.md](docs/01_setup_docker_database.md).

## Note / questioni aperte

- Il seed attuale è **minimo** (solo per i test di isolamento). Il seed ricco (30 stanze + KB) è il Passo 3.
- Convenzione: a ogni passo aggiornare `PROGRESS.md` + `README.md` e scrivere un report in `docs/0N_*.md`.
