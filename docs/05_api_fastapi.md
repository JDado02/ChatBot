# 05 — API FastAPI: sicurezza + ricerca (Passo 6, parte 1)

**Data:** 2026-07-01
**Stato:** ✅ Slice 1 completo e testato (offline, TestClient) — chat/LLM + sessioni Redis + lettura stanze = parte 2
**Corrisponde a:** Passo 6 della roadmap (in corso)

> Prima parte degli endpoint FastAPI: mette in fila la catena di sicurezza del
> Passo 5 e la ricerca semantica del Passo 4 dietro HTTP.

---

## 1. Cosa è stato realizzato

Pacchetto [`backend/app/api/`](../backend/app/api):

- **`deps.py`** — dipendenze FastAPI e provider **sostituibili nei test**
  (`app.dependency_overrides`): `resolve_tenant` (API key → tenant),
  `check_allowlist` (Origin/Referer), `enforce_rate_limit`, `require_session`
  (verifica del token Bearer).
- **`main.py`** — app con tre endpoint:
  - `GET /health` — liveness;
  - `POST /api/session` — verifica API key + dominio + rate limit ed emette un
    **token di sessione** a vita breve;
  - `POST /api/search` — richiede un token valido; ricerca semantica (RAG) sulla
    knowledge base del tenant.

Config estesa (`config.py`): `session_secret`, `session_ttl_seconds`,
`rate_limit`, `rate_window_seconds`.

---

## 2. Flusso di sicurezza

```
widget ──(X-API-Key + Origin)──▶ POST /api/session
        resolve_tenant → check_allowlist → rate_limit → issue_token
                                   ▼
                       { token, expires_in }
widget ──(Authorization: Bearer <token>)──▶ POST /api/search
        require_session (verifica firma+scadenza) → rate_limit → RAG
```

L'API key viaggia **solo** alla creazione della sessione; poi viaggia il token
temporaneo. Il `tenant_id` è dentro il token firmato: la ricerca non si fida di
input del client per decidere il tenant.

---

## 3. Decisioni tecniche

- **Provider iniettabili.** DB, resolver del tenant e searcher sono dietro
  provider FastAPI: nei test si sostituiscono con dei fake, così l'intera API si
  verifica **senza** database né modello.
- **Handler sincroni per ora.** Riusano i moduli sincroni (testati) dei Passi
  4–5. Il passaggio ad async (psycopg async, stesso pattern `set_config`) si farà
  quando serve throughput; l'interfaccia degli endpoint non cambia.
- **Errori chiari.** 401 (API key/token), 403 (dominio), 429 (rate limit), 422
  (validazione pydantic della query).

---

## 4. Verifica

`pytest` → **55 passed** (10 nuovi test API con TestClient): health; `/api/session`
con 401 (chiave assente o non valida), 403 (dominio non autorizzato), 429 (rate
limit), 200 (happy); `/api/search` con 401 (token mancante/non valido), 422
(query vuota), e **end-to-end** (session → token → search con risultati del tenant).

Avvio locale (con Docker + deps):
```bash
cd backend && pip install -r requirements.txt
uvicorn app.api.main:app --reload   # http://localhost:8000/docs
```

---

## 5. Prossimo passo (Passo 6, parte 2)

- **Lettura stanze**: endpoint per i dati strutturati delle camere (con
  `tenant_transaction`).
- **Sessioni conversazione su Redis**: storia chat con chiave `tenant_id:session_id`
  e TTL.
- **Chat con LLM**: endpoint `/api/chat` con la chiamata al modello dietro un
  adapter (come per gli embedding), stub finché non c'è vLLM/Ollama; qui si
  applicheranno le regole anti-allucinazione (system prompt + grounding sui dati
  RAG e sui dati stanza).
