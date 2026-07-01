# PROGRESS — AI Concierge

**Ultimo aggiornamento:** 2026-07-01
**Fase attuale:** Passi 1–7 fatti; Passo 8 parte codificabile fatta. Backend "offline" essenzialmente completo. Restano: verifiche runtime + integrazioni reali (modello LLM, SMTP, PMS) + Passo 9 (infra).

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
  - Passo 8 — **prenotazioni**: `booking.py` (salva richiesta `pending`), `email.py` (adapter + stub), `pms.py` (interfaccia + fake), endpoint `POST /api/booking`.
- **Test**: **98 unit/integration test offline**, tutti verdi (`cd backend && pytest`).

## ⚠️ Da verificare al prossimo avvio con Docker (+ Ollama)

Su questa macchina Docker non era avviabile (WSL2 senza distro): verifiche runtime rimandate.
```
# 1) DB + seed nuovo (init gira solo su volume vuoto)
docker compose down -v && docker compose up -d && ./db/test/run_isolation_test.sh   # atteso 4x PASS
# 2) embedding + ricerca
ollama pull bge-m3
cd backend && pip install -r requirements.txt
python scripts/generate_embeddings.py hotel_alpha hotel_beta
python scripts/search_demo.py hotel_alpha "a che ora è la colazione?"
# 3) API
uvicorn app.api.main:app --reload    # poi http://localhost:8000/docs
```

## Roadmap (sez. 14 del documento di architettura)

- [x] **1.** Ambiente locale Docker Compose: PostgreSQL + pgvector + Redis
- [x] **2.** RLS sulle tabelle + test isolamento — ✅ verificato (4/4 PASS)
- [x] **3.** Dati di test: 30 stanze (JSONB) + knowledge base — da caricare (`down -v`)
- [x] **4.** Pipeline embedding + ricerca semantica pgvector
- [x] **5.** Sicurezza widget: allowlist + rate limiting + token di sessione
- [x] **6.** Endpoint FastAPI: sicurezza + `/api/search` + `/api/rooms` + `/api/chat` (sessioni Redis, LLM stub)
- [x] **7.** System prompt anti-allucinazione + calcoli deterministici (conversioni, notti, prezzi)
- [~] **8.** Function calling — fatti: booking (`POST /api/booking`) + email stub + interfaccia PMS. Restano: LLM function-calling, SMTP reale, connettore PMS del cliente
- [ ] **9.** Server GPU dedicato EU (noleggio iniziale) con vLLM — infrastruttura (decisioni utente)

## Prossimo passo

Il backend "offline" è essenzialmente completo (Passi 1–8 nella loro parte codificabile). Le prossime azioni richiedono runtime o decisioni, in ordine consigliato:

1. **Verifica runtime end-to-end** (serve Docker funzionante — su questa macchina WSL2 non era pronto):
   `docker compose down -v && up -d` → test isolamento; `ollama pull bge-m3` + genera embedding + ricerca; `uvicorn app.api.main:app` e provare `/api/session`→`/api/chat`.
2. **LLM function calling** per la prenotazione: quando c'è un modello attivo (Ollama/vLLM) che supporta i tool, far invocare `create_booking` dalla conversazione.
3. **SMTP reale** (servizio email EU) al posto di `StubEmailSender` (aggiungere settaggi env + usare `SmtpEmailSender`).
4. **Connettore PMS del primo hotel reale** — su misura, in sopralluogo.
5. **Passo 9** — noleggio server GPU EU + vLLM: **decisione utente** (provider, budget).

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
- **2026-06-18** (dal remoto) — Ruolo `app_user` non-superuser; `FORCE ROW LEVEL SECURITY`; policy `SET LOCAL` + `current_setting(..., true)`. [docs/01](docs/01_setup_docker_database.md).

## Note / questioni aperte

- **Docker su questa macchina**: backend WSL2 non avviabile senza installare una distro (non fatto in autonomia). Verifiche runtime rimandate.
- **LLM in dev**: la chat (Passo 6/2) userà un adapter per il modello, testato con uno stub finché non c'è vLLM/Ollama.
- **Sync → async**: gli handler sono sincroni (riuso codice testato); passaggio ad async psycopg quando serve throughput, stesso pattern `set_config`.
- Convenzione: a ogni passo aggiornare `PROGRESS.md` + `README.md` e scrivere un report in `docs/0N_*.md`.
