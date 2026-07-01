# PROGRESS — AI Concierge

**Ultimo aggiornamento:** 2026-07-01
**Fase attuale:** Passi 1–8 + **widget frontend "Aria"** fatti e verificati (Docker OK, browser OK). Restano: modello LLM reale, integrazioni (SMTP/PMS), infrastruttura (Passo 9). Guida: [docs/GUIDA_TEST_E_PROSSIMI_PASSI.md](docs/GUIDA_TEST_E_PROSSIMI_PASSI.md).

> Segnalibro del progetto. Per riprendere una sessione: **`git pull`**, poi leggi questo file, l'ultimo commit e il report più recente in `docs/`.

## Stato in breve

- **Ambiente Docker**: PostgreSQL 16 + pgvector, Redis 7 (`docker-compose.yml`).
- **Schema DB** + **RLS multi-tenant** (`db/init/`), ruolo `app_user`, tabella `tenants` (API key/domini).
- **Seed ricco**: `hotel_alpha` 30 stanze (JSONB) + 14 schede KB; `hotel_beta` piccolo; tenant con API key.
- **Backend Python** (`backend/`):
  - Passo 4 — embedding (Ollama/Hash) + ricerca semantica pgvector, isolata per tenant.
  - Passo 5 — sicurezza widget: allowlist, token firmati, rate limit, lookup tenant.
  - Passo 6 — **API FastAPI**: `/health`, `/api/session` (token), `/api/search` (RAG), `/api/rooms`, `/api/chat` (RAG+storia Redis+LLM stub).
  - Passo 7 — **governance**: calcoli deterministici (`calc.py`: °C↔K, notti, prezzi) + system prompt anti-allucinazione (`prompt.py`).
  - Passo 8 — **prenotazioni**: `booking.py` (salva richiesta `pending`), `mailer.py` (adapter + stub), `pms.py` (interfaccia + fake), endpoint `POST /api/booking`.
  - Review — **CORS** per il widget; rinominato `email.py`→`mailer.py`; cleanup.
- **Widget frontend "Aria"** (`widget/`): chat embeddabile Vanilla JS + Shadow DOM, branding midnight+oro, integrazione API, persistenza conversazione, modalità demo. Testato nel browser.
- **Test**: **98 unit/integration test offline**, tutti verdi (`cd backend && pytest`).

## ✅ Verificato a runtime (2026-07-01, Docker OK)

Fix importante: gli script `.sh`/`.sql` avevano CRLF (rompeva l'init Docker) → risolto con `.gitattributes` (eol=lf). Poi verificato con successo:
- Init DB + **RLS 4×PASS** (incl. "30 stanze alpha"); **98 test** backend.
- Pipeline embedding + ricerca su **pgvector reale** (embedder fake) con **isolamento** (hotel_beta non vede alpha).
- **API vs DB reale**: `/api/session` (200), origin non autorizzato (403), `/api/rooms` (30), `/api/booking` (crea la richiesta).
- **NON** verificato: `/api/search` e `/api/chat` con **modello reale** (Ollama non installato).

Come rifare i test: [docs/GUIDA_TEST_E_PROSSIMI_PASSI.md](docs/GUIDA_TEST_E_PROSSIMI_PASSI.md).

## Roadmap (sez. 14 del documento di architettura)

- [x] **1.** Ambiente locale Docker Compose: PostgreSQL + pgvector + Redis
- [x] **2.** RLS sulle tabelle + test isolamento — ✅ verificato (4/4 PASS)
- [x] **3.** Dati di test: 30 stanze (JSONB) + knowledge base — ✅ caricato e verificato
- [x] **4.** Pipeline embedding + ricerca semantica pgvector
- [x] **5.** Sicurezza widget: allowlist + rate limiting + token di sessione
- [x] **6.** Endpoint FastAPI: sicurezza + `/api/search` + `/api/rooms` + `/api/chat` (sessioni Redis, LLM stub)
- [x] **7.** System prompt anti-allucinazione + calcoli deterministici (conversioni, notti, prezzi)
- [~] **8.** Function calling — fatti: booking (`POST /api/booking`) + email stub + interfaccia PMS. Restano: LLM function-calling, SMTP reale, connettore PMS del cliente
- [ ] **9.** Server GPU dedicato EU (noleggio iniziale) con vLLM — infrastruttura (decisioni utente)

## Prossimo passo

Backend + widget completi e verificati (Docker + browser). Le prossime azioni richiedono un modello, servizi esterni o decisioni:

1. **Modello LLM reale**: `ollama pull bge-m3` e `ollama pull llama3`, poi provare ricerca e chat vere (widget in `?mode=live`). Poi valutare vLLM.
2. **LLM function calling** per la prenotazione: far invocare `create_booking` dalla conversazione (serve un modello con tool).
3. **SMTP reale** (servizio email EU) al posto di `StubEmailSender`.
4. **Connettore PMS del primo hotel reale** — su misura, in sopralluogo.
5. **Passo 9** — server GPU EU + vLLM: **decisione utente** (provider, budget).
6. Migliorie widget (vedi [docs/09](docs/09_widget_frontend.md)): streaming risposta, markdown-lite, temi per-hotel, build/minify.

## Decisioni prese

- **2026-07-01** — Flusso a **singolo agente**, "autonomia a blocchi", no multi-agente. Motivo: budget token (Pro) + coerenza. Stato in `PROGRESS.md` + commit piccoli e frequenti.
- **2026-07-01** — Integrato con rebase il lavoro pre-esistente dal remoto (Passi 1–2). Ruoli file: `CLAUDE.md`=regole, `PROGRESS.md`=stato, `README.md`=panoramica, `docs/`=architettura + report per-passo.
- **2026-07-01** — Passo 3: seed via `CROSS JOIN`; `ALTER DEFAULT PRIVILEGES`. [docs/02](docs/02_seed_dati_test.md).
- **2026-07-01** — Passo 4: backend **sincrono** per la pipeline; embedder come **adapter**; isolamento via `tenant_transaction`. [docs/03](docs/03_embedding_ricerca_semantica.md).
- **2026-07-01** — Passo 5: tabella `tenants` **fuori** dalla RLS (lookup API key), `app_user` solo SELECT; token HMAC senza dipendenze; allowlist **fail-closed**. [docs/04](docs/04_sicurezza_widget.md).
- **2026-07-01** — Passo 6/1: endpoint con **provider iniettabili** (test via `dependency_overrides`, senza DB/modello); handler sincroni che riusano i moduli testati; il `tenant_id` viaggia dentro il token firmato. [docs/05](docs/05_api_fastapi.md).
- **2026-07-01** — Passo 6/2: `answer()` della chat disaccoppiato dal DB (riceve `search_fn`) → orchestrazione testabile offline; `session_id` preso dal token firmato; sessioni Redis con TTL (GDPR); LLM dietro adapter (Stub/Ollama). [docs/06](docs/06_api_chat_sessioni.md).
- **2026-07-01** — Passo 7: calcoli deterministici in `calc.py` (l'IA non calcola nulla); regole+prompt in `prompt.py`; conversione °C→K già pronta nei fatti stanza. [docs/07](docs/07_governance_risposte.md).
- **2026-07-01** — Passo 8: prenotazione come **richiesta** `pending` (non conferma); email e PMS dietro adapter (stub/fake in dev); `reception_email` per-tenant; RLS anche in scrittura (`WITH CHECK`). [docs/08](docs/08_prenotazioni_pms.md).
- **2026-07-01** — Fix CRLF: `.gitattributes` con `eol=lf` per `*.sh`/`*.sql` (lo shebang con CRLF rompeva l'init Docker). Cruciale col multi-computer.
- **2026-07-01** — Review: aggiunto **CORS** (la sicurezza vera resta l'allowlist server-side); `email.py`→`mailer.py` (no shadow dello stdlib); scritta la guida test+roadmap.
- **2026-07-01** — Widget "Aria": Vanilla JS + **Shadow DOM**, **zero risorse esterne** (GDPR); testo escapato (anti-XSS); persistenza in `sessionStorage`; errori del modello resi **503+CORS** (non 500) per messaggi chiari nel widget. [docs/09](docs/09_widget_frontend.md).
- **2026-06-18** (dal remoto) — Ruolo `app_user` non-superuser; `FORCE ROW LEVEL SECURITY`; policy `SET LOCAL` + `current_setting(..., true)`. [docs/01](docs/01_setup_docker_database.md).

## Note / questioni aperte

- **Docker**: ora funziona (era WSL2). Se un clone fresco su Windows dà errori di init, controllare che `.sh`/`.sql` siano LF (li forza `.gitattributes`).
- **Prossimo passo #1: il widget frontend** (Vanilla JS + Shadow DOM) — è il pezzo mancante più importante per un prodotto dimostrabile.
- **LLM in dev**: `/api/search` e `/api/chat` richiedono Ollama (`ollama pull bge-m3` e `llama3`); senza modello gli altri endpoint funzionano.
- **Sync → async**: gli handler sono sincroni (riuso codice testato); passaggio ad async psycopg quando serve throughput, stesso pattern `set_config`.
- **CI**: GitHub Action `backend-tests` esegue i 98 test a ogni push. Se non parte, abilitare GitHub Actions nella repo (Settings → Actions).
- **Settaggi**: nuovi in `.env.example` (SESSION_SECRET, modelli, rate limit, TTL). In prod cambiare `SESSION_SECRET`.
- Convenzione: a ogni passo aggiornare `PROGRESS.md` + `README.md` e scrivere un report in `docs/0N_*.md`.
