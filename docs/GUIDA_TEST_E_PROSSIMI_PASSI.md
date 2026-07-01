# Guida: come testare il progetto + prossimi passi

Guida pratica per **provare l'AI Concierge dall'inizio alla fine** e per capire
**cosa manca** per arrivare in produzione. Aggiornata al 2026-07-01, dopo la
verifica runtime completa su Windows + Docker.

> In breve: il **backend è completo e verificato** (multi-tenant con RLS, RAG,
> sicurezza widget, chat, prenotazioni). Mancano il **widget frontend**, il
> **modello LLM reale** e le **integrazioni** (SMTP, PMS) + l'infrastruttura.

---

## Prerequisiti

- **Docker Desktop** (con backend WSL2 funzionante su Windows).
- **Python 3.11+** (testato con 3.12).
- *(Opzionale, per LLM/embedding reali)* **[Ollama](https://ollama.com)**.

---

## 1. Avvio dell'ambiente (PostgreSQL + Redis)

```bash
cp .env.example .env          # solo la prima volta
docker compose up -d
docker compose ps             # attendere che siano "healthy"
```

Gli script in `db/init/` girano **solo al primo avvio** (volume vuoto) e creano:
ruolo `app_user`, schema con RLS, e i dati di test (hotel_alpha 30 stanze + KB,
hotel_beta piccolo, tenant con API key). Dopo modifiche a schema/seed:

```bash
docker compose down -v && docker compose up -d   # re-init da zero
```

## 2. Test di isolamento multi-tenant (RLS)

```bash
./db/test/run_isolation_test.sh
```

**Atteso:** `4x PASS` e `== TUTTI I TEST SUPERATI ==` (incl. "vedo 30 stanze
alpha, 0 di altri hotel"). Dimostra che un hotel non può vedere i dati di un altro.

## 3. Test automatici del backend (98 test, offline)

```bash
cd backend
pip install -r requirements.txt
pytest
```

**Atteso:** `98 passed`. Non serve né DB né modello: usano fake/stub. Coprono
vettori, embedder, sicurezza (allowlist, token, rate limit), API (TestClient),
calcoli deterministici, prenotazioni.

## 4. Pipeline embedding + ricerca semantica

**Offline** (senza modello, per provare il "plumbing" contro pgvector reale):

```bash
cd backend
python scripts/generate_embeddings.py hotel_alpha hotel_beta --fake
python scripts/search_demo.py hotel_alpha "a che ora e la colazione?" --fake
python scripts/search_demo.py hotel_beta  "colazione" --fake   # vede SOLO schede beta (RLS)
```

**Reale** (risultati semanticamente sensati, richiede Ollama):

```bash
ollama pull bge-m3
cd backend
python scripts/generate_embeddings.py hotel_alpha hotel_beta
python scripts/search_demo.py hotel_alpha "a che ora e la colazione?"
# atteso: la scheda "Colazione a buffet" tra i primi risultati
```

## 5. API HTTP

```bash
cd backend
uvicorn app.api.main:app --reload
```

Modo più semplice: aprire **http://localhost:8000/docs** (Swagger UI) e provare
gli endpoint. Da terminale (Git Bash):

```bash
API=http://localhost:8000

# 1) bootstrap sessione: API key + dominio autorizzato -> token
TOKEN=$(curl -s -X POST $API/api/session \
  -H "X-API-Key: pk_alpha_dev_0001" -H "Origin: http://localhost" \
  | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

# 2) lettura stanze (30) e ricerca (serve Ollama, altrimenti 500)
curl -s $API/api/rooms -H "Authorization: Bearer $TOKEN"
curl -s -X POST $API/api/search -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"query":"colazione","k":3}'

# 3) richiesta di prenotazione (salva + email stub alla reception)
curl -s -X POST $API/api/booking -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"guest_name":"Mario Rossi","guest_email":"mario@example.com","check_in":"2026-09-01","check_out":"2026-09-03","num_guests":2}'

# 4) chat (serve un modello LLM attivo, es. Ollama con llama3)
curl -s -X POST $API/api/chat -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"message":"a che ora e la colazione?"}'
```

**Note:**
- `/api/session` senza `X-API-Key` → 401; con `Origin` non autorizzato → 403.
- `/api/search` e `/api/chat` richiedono **Ollama** (embedding/chat). Senza, gli
  altri endpoint funzionano lo stesso.
- Chiavi/domini di test sono nel seed (`db/init/02_seed.sql`): `hotel_alpha` usa
  `pk_alpha_dev_0001` con domini `alpha.example.com`, `localhost`.

---

## Cosa è stato verificato a runtime (2026-07-01)

| Area | Esito |
|---|---|
| Init Docker (schema, RLS, seed 30 stanze) | ✅ |
| Test isolamento RLS | ✅ 4×PASS |
| Suite backend | ✅ 98 passed |
| Embedding + ricerca su pgvector (fake) + isolamento | ✅ |
| API vs DB reale: session/rooms/booking + allowlist (403) | ✅ |
| Ricerca/chat con **modello reale** | ⏳ non testato (Ollama non installato) |

---

## Prossimi passi (in ordine di priorità)

### 1. Widget frontend (il pezzo mancante più importante)
Il componente che vede l'utente non esiste ancora: **Vanilla JS + Shadow DOM**
(come da architettura), che chiama `/api/session` e poi `/api/chat`. Serve per
avere il prodotto dimostrabile end-to-end sul sito di un hotel.

### 2. Modello LLM reale
- **Dev:** Ollama (`ollama pull bge-m3` + `ollama pull llama3`), poi provare
  `/api/search` e `/api/chat` reali.
- **Prod:** vLLM su GPU (vedi punto 6).

### 3. Function calling per la prenotazione
Far sì che sia l'LLM, in conversazione, a raccogliere i dati e invocare la
creazione della richiesta (oggi l'endpoint `/api/booking` c'è, ma va chiamato
esplicitamente). Richiede un modello che supporti i tool.

### 4. Integrazioni reali
- **SMTP EU**: sostituire `StubEmailSender` con `SmtpEmailSender` (config via env).
- **Connettore PMS** del primo hotel: implementare `PMSAdapter` su misura
  (API/channel manager/file), con cache breve su Redis.

### 5. Robustezza per la produzione
- **Rate limiter su Redis** (`RedisRateLimiter`) al posto di quello in-memory
  (necessario con più worker/processi).
- **Passaggio async** del percorso richiesta (psycopg async) se serve throughput.
- **Logging strutturato** + gestione errori centralizzata.
- **Migrazioni DB** (oggi gli script girano solo al primo avvio): introdurre uno
  strumento di migrazione per evolvere lo schema senza `down -v`.
- **Segreti**: cambiare `SESSION_SECRET` e le password in produzione.
- **TTL sessione**: valutare un valore più lungo o un endpoint di refresh (ora 300s).

### 6. Infrastruttura (Passo 9)
- **Dockerfile** per il backend + servizio nel `docker compose` + **Caddy** per
  HTTPS automatico.
- **Server GPU dedicato EU** (noleggio Hetzner/OVH) con **vLLM**. Decisione da
  prendere: provider e budget.

---

Per lo stato dettagliato e la roadmap completa vedi [`PROGRESS.md`](../PROGRESS.md);
i report tecnici per ogni passo sono in [`docs/`](.).
