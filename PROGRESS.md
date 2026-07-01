# PROGRESS — AI Concierge

**Ultimo aggiornamento:** 2026-07-01
**Fase attuale:** Passi 1–5 realizzati. In corso: Passo 6.

> Segnalibro del progetto. Per riprendere una sessione: **`git pull`**, poi leggi questo file, l'ultimo commit e il report più recente in `docs/`.

## Stato in breve

- **Ambiente Docker**: PostgreSQL 16 + pgvector, Redis 7 (`docker-compose.yml`).
- **Schema DB** + **RLS multi-tenant** (`db/init/`), ruolo non-superuser `app_user`, default privileges, tabella `tenants` (config API key/domini).
- **Seed ricco**: `hotel_alpha` 30 stanze (JSONB) + 14 schede KB; `hotel_beta` piccolo; seed tenant con API key + domini.
- **Backend Python** (`backend/`): pipeline **embedding** + **ricerca semantica** pgvector (Passo 4) e **sicurezza widget** (allowlist, token firmati, rate limit, lookup tenant — Passo 5).
- **Test**: 45 unit test offline, tutti verdi (`cd backend && pytest`).

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
```

## Roadmap (sez. 14 del documento di architettura)

- [x] **1.** Ambiente locale Docker Compose: PostgreSQL + pgvector + Redis
- [x] **2.** RLS sulle tabelle + test isolamento — ✅ verificato (4/4 PASS)
- [x] **3.** Dati di test: 30 stanze (JSONB) + knowledge base — scritto+validato, da caricare (`down -v`)
- [x] **4.** Pipeline embedding + ricerca semantica pgvector — codice+test offline
- [x] **5.** Sicurezza widget: allowlist domini + rate limiting + token di sessione — primitive+test offline
- [ ] **6.** Endpoint FastAPI: chat, sessioni Redis, RAG sulla knowledge base, lettura stanze  ← PROSSIMO
- [ ] **7.** System prompt: regole di risposta + dati/calcoli deterministici (prezzi, orari, conversioni)
- [ ] **8.** Function calling: richiesta prenotazione (email reception) + adapter PMS del primo hotel
- [ ] **9.** Server GPU dedicato EU (noleggio iniziale) con vLLM

## Prossimo passo

**Passo 6:** endpoint **FastAPI (async)**. Montare le primitive del Passo 5 come dependency (API key → tenant → allowlist Origin/Referer → rate limit → token di sessione); endpoint di ricerca/chat che usa il RAG del Passo 4; gestione sessioni conversazione su Redis (chiave `tenant_id:session_id`, TTL). Il percorso richiesta usa psycopg **async** con lo stesso pattern `set_config` per la RLS. La chiamata all'LLM (vLLM/Ollama) resterà stub finché non c'è il modello.

## Decisioni prese

- **2026-07-01** — Flusso a **singolo agente**, "autonomia a blocchi", no multi-agente. Motivo: budget token (Pro) + coerenza sui vincoli. Stato in `PROGRESS.md` + commit piccoli e frequenti.
- **2026-07-01** — Integrato con rebase il lavoro pre-esistente dal remoto (Passi 1–2). Ruoli file: `CLAUDE.md`=regole, `PROGRESS.md`=stato, `README.md`=panoramica, `docs/`=architettura + report per-passo.
- **2026-07-01** — Passo 3: seed via `CROSS JOIN` (6 archetipi × 5 piani); `ALTER DEFAULT PRIVILEGES`. Vedi [docs/02](docs/02_seed_dati_test.md).
- **2026-07-01** — Passo 4: backend **sincrono** per la pipeline batch (async al Passo 6); embedder come **adapter** (Ollama/Hash); isolamento via `tenant_transaction`. Vedi [docs/03](docs/03_embedding_ricerca_semantica.md).
- **2026-07-01** — Passo 5: tabella `tenants` **fuori** dalla RLS per-tenant (è il lookup dell'API key), `app_user` solo `SELECT`; token di sessione firmati HMAC senza dipendenze; allowlist **fail-closed**. Vedi [docs/04](docs/04_sicurezza_widget.md).
- **2026-06-18** (dal remoto) — Ruolo `app_user` non-superuser; `FORCE ROW LEVEL SECURITY`; policy `SET LOCAL` + `current_setting(..., true)` fail-safe. Vedi [docs/01](docs/01_setup_docker_database.md).

## Note / questioni aperte

- **Docker su questa macchina**: backend WSL2 non avviabile senza installare una distro (modifica di sistema non fatta in autonomia). Verifiche runtime rimandate.
- **LLM in dev**: per il Passo 6 il modello (vLLM/Ollama) potrebbe non essere disponibile qui; l'endpoint chat verrà scritto con la chiamata all'LLM isolata dietro un adapter (come per gli embedding) e testato con uno stub.
- Convenzione: a ogni passo aggiornare `PROGRESS.md` + `README.md` e scrivere un report in `docs/0N_*.md`.
