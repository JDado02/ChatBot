# Backend — AI Concierge

Backend Python del progetto: **API FastAPI** che unisce ricerca semantica (RAG),
sicurezza del widget, chat con memoria, prenotazioni e governance
anti-allucinazione — tutto **isolato per tenant** dalla Row-Level Security.

## Struttura

```
backend/
├── app/
│   ├── config.py       # settings da env (DB, Ollama, sessione, rate limit, CORS)
│   ├── db.py           # connect() + tenant_transaction()  ← imposta la RLS
│   ├── vectors.py      # utility pgvector pure (to_pgvector, cosine)
│   ├── embeddings.py   # Embedder: OllamaEmbedder (reale) + HashEmbedder (offline)
│   ├── search.py       # store_embeddings() + semantic_search()
│   ├── rooms.py        # lettura dati stanza (via tenant_transaction)
│   ├── sessions.py     # memoria conversazioni (InMemory / Redis, TTL)
│   ├── llm.py          # adapter LLM: OllamaLLM (reale) + StubLLM (offline)
│   ├── chat.py         # orchestrazione RAG + storia + LLM (answer)
│   ├── prompt.py       # system prompt anti-allucinazione + fatti stanza
│   ├── calc.py         # calcoli deterministici (°C↔K, notti, prezzi)
│   ├── booking.py      # richiesta di prenotazione (validazione + INSERT)
│   ├── mailer.py       # invio email reception (Smtp / Stub)
│   ├── pms.py          # adapter PMS (interfaccia + Null/Fake)
│   └── api/
│       ├── deps.py     # dipendenze/sicurezza (provider iniettabili)
│       └── main.py     # app FastAPI + endpoint
├── scripts/            # generate_embeddings.py, search_demo.py (CLI)
├── tests/              # 98 test offline (pytest)
└── requirements.txt
```

## Endpoint (FastAPI)

| Metodo · path | Cosa fa | Auth |
|---|---|---|
| `GET /health` | liveness | — |
| `POST /api/session` | API key + dominio + rate limit → emette **token** | API key + Origin |
| `POST /api/search` | ricerca semantica (RAG) sulla KB del tenant | token |
| `GET /api/rooms` · `GET /api/rooms/{n}` | dati stanza | token |
| `POST /api/chat` | RAG + memoria Redis + LLM (con grounding) | token |
| `POST /api/booking` | richiesta di prenotazione → email reception | token |

Catena di sicurezza: **API key → tenant → allowlist Origin/Referer → rate limit →
token di sessione firmato**. Il `tenant_id` viaggia dentro il token.

## Concetti chiave

- **Isolamento RLS.** Ogni accesso ai dati passa da `tenant_transaction(conn, tenant_id)`
  che esegue `set_config('app.current_tenant', <id>, true)` (equivalente
  parametrizzabile di `SET LOCAL`). Il backend si connette come `app_user`
  (non-superuser), quindi la RLS è **sempre** applicata.
- **Adapter intercambiabili.** Embedding (`OllamaEmbedder`/`HashEmbedder`) e LLM
  (`OllamaLLM`/`StubLLM`) hanno la stessa interfaccia: in dev Ollama, in CI/offline
  gli stub, in prod si potrà usare vLLM senza toccare il resto.
- **Anti-allucinazione.** Numeri/prezzi/conversioni li calcola `calc.py`; l'IA li
  riporta soltanto (vedi `prompt.py`).
- **Provider iniettabili.** Gli endpoint dipendono da provider sostituibili nei
  test (`app.dependency_overrides`), quindi l'API si testa senza DB/modello.

## Avvio e uso

```bash
cd backend
pip install -r requirements.txt

# API HTTP (poi http://localhost:8000/docs)
uvicorn app.api.main:app --reload

# Pipeline embedding + ricerca (offline con --fake, oppure reale con Ollama)
python scripts/generate_embeddings.py hotel_alpha hotel_beta --fake
python scripts/search_demo.py hotel_alpha "a che ora è la colazione?" --fake
```

Prerequisiti runtime: container su (`docker compose up -d` dalla radice); per
ricerca/chat **reali**, [Ollama](https://ollama.com) con `ollama pull bge-m3` e
`ollama pull llama3`.

## Test

```bash
cd backend && pip install -r requirements.txt && pytest   # atteso: 98 passed
```

I test sono **offline** (fake/stub, niente DB né modello): vettori, embedder,
sicurezza (allowlist, token, rate limit), API (TestClient), calcoli, prenotazioni.

## Variabili d'ambiente (default dev in `.env.example`)

| Var | Default | Note |
|---|---|---|
| `DB_HOST` / `POSTGRES_PORT` / `POSTGRES_DB` | `localhost` / `5432` / `concierge` | |
| `APP_DB_USER` / `APP_DB_PASSWORD` | `app_user` / `app_dev_only` | ruolo non-superuser (RLS) |
| `REDIS_HOST` / `REDIS_PORT` | `localhost` / `6379` | memoria conversazioni |
| `CONVERSATION_TTL_SECONDS` | `3600` | scadenza chat (privacy) |
| `OLLAMA_URL` | `http://localhost:11434` | |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` | `bge-m3` / `1024` | deve combaciare con `vector(1024)` |
| `CHAT_MODEL` | `llama3` | modello chat Ollama |
| `SESSION_SECRET` | `dev-...` | **in prod: segreto forte** |
| `SESSION_TTL_SECONDS` | `300` | vita del token di sessione |
| `RATE_LIMIT` / `RATE_WINDOW_SECONDS` | `60` / `60` | rate limiting |
| `CORS_ALLOW_ORIGINS` | `*` | origini permesse al browser |

> Nota: gli handler API sono **sincroni** (riuso dei moduli testati); il passaggio
> ad async psycopg si farà quando serve throughput, con lo stesso pattern `set_config`.
