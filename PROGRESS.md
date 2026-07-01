# PROGRESS — AI Concierge

**Ultimo aggiornamento:** 2026-07-01
**Fase attuale:** Passi 1–4 realizzati. In corso: Passo 5.

> Segnalibro del progetto. Per riprendere una sessione: **`git pull`**, poi leggi questo file, l'ultimo commit e il report più recente in `docs/`.

## Stato in breve

- **Ambiente Docker**: PostgreSQL 16 + pgvector, Redis 7 (`docker-compose.yml`).
- **Schema DB** + **RLS multi-tenant** (`db/init/`), ruolo non-superuser `app_user`, default privileges per tabelle future.
- **Seed ricco**: `hotel_alpha` 30 stanze (JSONB completo) + 14 schede KB; `hotel_beta` piccolo per il contrasto.
- **Backend Python** (`backend/`): pipeline di **embedding** (Ollama / HashEmbedder offline) + **ricerca semantica** pgvector, isolata per tenant. 18 unit test passano.
- Verifiche statiche: seed valido (grammatica Postgres reale) + query di ricerca valide.

## ⚠️ Da verificare al prossimo avvio con Docker (+ Ollama)

Su questa macchina Docker Desktop non era avviabile (WSL2 senza distro), quindi le verifiche runtime sono rimandate:
```
# 1) DB + seed nuovo (gli init girano solo su volume vuoto)
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
- [x] **4.** Pipeline embedding (modello locale) + ricerca semantica pgvector — codice+test offline, runtime da verificare
- [ ] **5.** Sicurezza widget: allowlist domini + rate limiting + token di sessione  ← PROSSIMO
- [ ] **6.** Endpoint FastAPI: chat, sessioni Redis, RAG sulla knowledge base, lettura stanze
- [ ] **7.** System prompt: regole di risposta + dati/calcoli deterministici (prezzi, orari, conversioni)
- [ ] **8.** Function calling: richiesta prenotazione (email reception) + adapter PMS del primo hotel
- [ ] **9.** Server GPU dedicato EU (noleggio iniziale) con vLLM

## Prossimo passo

**Passo 5:** sicurezza del widget — allowlist domini (Origin/Referer) + rate limiting + token di sessione a vita breve. In alternativa, anticipare parte del **Passo 6** (endpoint FastAPI) per esporre la ricerca via HTTP e provarla dal browser. Valutare quale dà più valore verificabile subito.

## Decisioni prese

- **2026-07-01** — Flusso a **singolo agente**, "autonomia a blocchi", no multi-agente. Motivo: budget token (Pro) + coerenza sui vincoli. Stato in `PROGRESS.md` + commit piccoli e frequenti.
- **2026-07-01** — Integrato con rebase il lavoro pre-esistente dal remoto (Passi 1–2). Ruoli file: `CLAUDE.md`=regole, `PROGRESS.md`=stato, `README.md`=panoramica, `docs/`=architettura + report per-passo.
- **2026-07-01** — Passo 3: seed via `CROSS JOIN` (6 archetipi × 5 piani); `ALTER DEFAULT PRIVILEGES`. Vedi [docs/02](docs/02_seed_dati_test.md).
- **2026-07-01** — Passo 4: backend Python **sincrono** per la pipeline batch (async al Passo 6 con FastAPI, stesso pattern `set_config`); embedder come **adapter** (Ollama/Hash); isolamento tenant via `tenant_transaction`. Vedi [docs/03](docs/03_embedding_ricerca_semantica.md).
- **2026-06-18** (dal remoto) — Ruolo `app_user` non-superuser; `FORCE ROW LEVEL SECURITY`; policy `SET LOCAL` + `current_setting(..., true)` fail-safe. Vedi [docs/01](docs/01_setup_docker_database.md).

## Note / questioni aperte

- **Docker su questa macchina**: backend WSL2 non avviabile senza installare una distro (modifica di sistema non fatta in autonomia). Verifiche runtime rimandate.
- **Scelta Passo 5 vs 6**: decidere se fare prima la sicurezza widget o anticipare gli endpoint FastAPI (più facile da provare dal browser). Vedi "Prossimo passo".
- Convenzione: a ogni passo aggiornare `PROGRESS.md` + `README.md` e scrivere un report in `docs/0N_*.md`.
