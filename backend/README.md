# Backend — pipeline embedding & ricerca semantica (Passo 4)

Prima base di codice Python del backend: genera gli embedding della knowledge
base con un modello locale e fa **ricerca semantica** (RAG) con pgvector,
sempre **isolata per tenant** dalla Row-Level Security.

## Struttura

```
backend/
├── app/
│   ├── config.py       # settings da env (DB come app_user, Ollama, dim=1024)
│   ├── db.py           # connect() + tenant_transaction() ← imposta la RLS
│   ├── embeddings.py   # Embedder: OllamaEmbedder (reale) + HashEmbedder (offline)
│   ├── vectors.py      # utility pgvector pure (to_pgvector, cosine) — testabili
│   └── search.py       # store_embeddings() + semantic_search()
├── scripts/
│   ├── generate_embeddings.py   # popola knowledge_base.embedding
│   └── search_demo.py           # prova la ricerca da CLI
├── tests/              # unit test offline (nessun DB/modello richiesto)
└── requirements.txt
```

## Concetti chiave

- **Isolamento RLS.** Ogni operazione passa da `tenant_transaction(conn, tenant_id)`,
  che esegue `set_config('app.current_tenant', <id>, true)` (equivalente
  parametrizzabile di `SET LOCAL`). La ricerca vede quindi **solo** le schede
  del tenant corrente.
- **Embedder intercambiabile.** `OllamaEmbedder` per gli embedding reali (dev),
  `HashEmbedder` deterministico e offline per testare la pipeline senza modello.
  Stessa interfaccia → il resto del codice non cambia.
- **Sync ora, async al Passo 6.** Questa è una pipeline batch: psycopg in
  modalità sincrona. Il percorso richiesta di FastAPI userà psycopg async con
  lo **stesso** pattern `set_config`.

## Prerequisiti

- Container su: `docker compose up -d` (dalla root del progetto).
- Embedding reali: [Ollama](https://ollama.com) in esecuzione + modello scaricato:
  ```bash
  ollama pull bge-m3
  ```
- Dipendenze Python: `pip install -r requirements.txt`.

## Uso

```bash
cd backend

# 1) genera gli embedding (reale, con Ollama)
python scripts/generate_embeddings.py hotel_alpha hotel_beta

#    …oppure offline, solo per verificare il plumbing (risultati non sensati):
python scripts/generate_embeddings.py hotel_alpha --fake

# 2) prova la ricerca
python scripts/search_demo.py hotel_alpha "a che ora è la colazione?"
```

## Test

```bash
cd backend
pip install -r requirements.txt
pytest
```

I test sono **offline**: coprono le utility sui vettori e gli embedder
(HashEmbedder + OllamaEmbedder con trasporto HTTP finto). Non richiedono né il
database né un modello. La verifica end-to-end (embedding reali + ricerca su
pgvector) va fatta con Docker + Ollama attivi.

## Variabili d'ambiente (con default dev)

| Var | Default | Note |
|---|---|---|
| `DB_HOST` | `localhost` | |
| `POSTGRES_PORT` | `5432` | |
| `POSTGRES_DB` | `concierge` | |
| `APP_DB_USER` | `app_user` | ruolo non-superuser (RLS) |
| `APP_DB_PASSWORD` | `app_dev_only` | da `.env` |
| `OLLAMA_URL` | `http://localhost:11434` | |
| `EMBEDDING_MODEL` | `bge-m3` | |
| `EMBEDDING_DIM` | `1024` | deve combaciare con `vector(1024)` |
