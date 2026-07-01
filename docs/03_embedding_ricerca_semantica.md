# 03 — Pipeline di embedding + ricerca semantica (RAG)

**Data:** 2026-07-01
**Stato:** ✅ Codice completo e testato offline — ⚠️ verifica end-to-end (embedding reali + ricerca su pgvector) da fare con Docker + Ollama
**Corrisponde a:** Passo 4 della roadmap

> Prima base di codice Python del backend. Genera gli embedding della knowledge
> base con un modello locale e fa ricerca semantica con pgvector, sempre
> isolata per tenant dalla RLS.

---

## 1. Cosa è stato realizzato

Nuovo pacchetto in [`backend/`](../backend/README.md):

- **`app/db.py`** — `connect()` + `tenant_transaction()`. Quest'ultima è il pezzo
  architetturale critico: imposta l'identità del tenant con
  `set_config('app.current_tenant', <id>, true)` all'inizio di ogni transazione
  (equivalente parametrizzabile di `SET LOCAL`, sicuro contro SQL injection).
- **`app/embeddings.py`** — interfaccia `Embedder` con due implementazioni:
  - `OllamaEmbedder`: embedding reali da modello locale (dev), endpoint
    `/api/embeddings`, con validazione della dimensione (deve essere 1024);
  - `HashEmbedder`: deterministico e **offline**, per testare la pipeline senza
    modello (nessuna qualità semantica).
- **`app/vectors.py`** — utility pure per pgvector (`to_pgvector`, `parse_pgvector`,
  `cosine_similarity`), senza dipendenze da DB/rete → testabili al 100%.
- **`app/search.py`** — `store_embeddings()` (popola gli embedding mancanti, a
  batch) e `semantic_search()` (top-K schede per distanza coseno `<=>`).
- **`scripts/generate_embeddings.py`** e **`scripts/search_demo.py`** — CLI per
  generare gli embedding e provare la ricerca.
- **`tests/`** — 18 unit test offline.

---

## 2. Decisioni tecniche

### 2.1 `set_config(..., true)` invece di `SET LOCAL` interpolato
`SET LOCAL app.current_tenant = ...` non accetta parametri bind per il valore:
interpolare la stringa sarebbe un rischio di SQL injection. `set_config(k, v, true)`
è l'equivalente parametrizzabile ed è "local" alla transazione (terzo arg `true`),
quindi non resta attaccato alla connessione riusata dal pool.

### 2.2 Embedder come adapter intercambiabile
La ricerca e la pipeline dipendono solo dall'interfaccia `Embedder`. In dev si usa
Ollama; in CI/offline `HashEmbedder`; in produzione si potrà scrivere un embedder
verso vLLM o un server dedicato senza toccare il resto.

### 2.3 Formattazione manuale del vettore
`to_pgvector` produce il literal `'[...]'` castato con `%s::vector`. Così non
serve dipendere dal pacchetto `pgvector` a livello di import; l'SQL resta esplicito.

### 2.4 Sync ora, async al Passo 6
La pipeline è un job batch: psycopg sincrono, più semplice e testabile. Il percorso
richiesta di FastAPI (Passo 6) userà psycopg **async** con lo stesso pattern
`set_config`. L'SQL e la logica non cambiano.

### 2.5 Isolamento per tenant "gratis"
`semantic_search` gira dentro `tenant_transaction`: la RLS fa sì che la query veda
solo le schede del tenant corrente. Il multi-tenant nel RAG è quindi garantito dal
database, non dal codice applicativo.

---

## 3. Verifica

**Fatto (offline, su questa macchina):**
- `pytest` → **18 passed**: utility vettoriali, `HashEmbedder` (determinismo,
  normalizzazione L2, dimensione), `OllamaEmbedder` con trasporto HTTP finto
  (parsing, validazione dimensione, errori).
- Import dell'intero grafo dei moduli OK; script compilano.
- Le query SQL di `search.py` validate contro la **grammatica reale di Postgres**
  (`pglast`), incluso l'operatore `<=>` e il cast `::vector`.

**Da fare (runtime, con Docker + Ollama):**
```bash
docker compose up -d                    # dalla root
ollama pull bge-m3                       # modello di embedding
cd backend && pip install -r requirements.txt
python scripts/generate_embeddings.py hotel_alpha hotel_beta
python scripts/search_demo.py hotel_alpha "a che ora è la colazione?"
```
Atteso: la scheda "Colazione a buffet" tra i primi risultati per hotel_alpha, e
**nessuna** scheda di hotel_beta (isolamento RLS).

---

## 4. Prossimo passo

**Passo 5:** sicurezza del widget — allowlist domini (Origin/Referer) + rate
limiting + token di sessione a vita breve. In alternativa si può anticipare parte
del **Passo 6** (endpoint FastAPI) per esporre la ricerca via HTTP e provarla dal
browser.
