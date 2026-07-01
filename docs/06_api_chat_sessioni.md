# 06 — API: lettura stanze, sessioni Redis, chat (Passo 6, parte 2)

**Data:** 2026-07-01
**Stato:** ✅ Passo 6 completo (codice + test offline) — ⚠️ runtime (DB + Redis + LLM) da verificare
**Corrisponde a:** Passo 6 della roadmap (completamento)

> Completa gli endpoint FastAPI: lettura dei dati stanza, memoria conversazione
> su Redis e l'endpoint di chat che orchestra RAG + storia + LLM con grounding.

---

## 1. Cosa è stato realizzato

- **Lettura stanze** (`app/rooms.py` + endpoint `GET /api/rooms`, `GET /api/rooms/{n}`):
  dati strutturati delle camere via `tenant_transaction` (RLS). 404 se assente.
- **Memoria conversazioni** (`app/sessions.py`): `InMemorySessionStore` (test) e
  `RedisSessionStore` (produzione). Chiave `tenant_id:session_id`, lista JSON con
  **trim** agli ultimi N messaggi e **TTL** (le sessioni scadono da sole → privacy).
- **Adapter LLM** (`app/llm.py`): `OllamaLLM` (chat reale via `/api/chat`) e
  `StubLLM` (deterministico, offline).
- **Orchestrazione chat** (`app/chat.py`): `answer()` fa ricerca RAG, salva il
  messaggio, costruisce il system prompt con **CONTESTO** recuperato + regole
  anti-allucinazione, chiama l'LLM, salva la risposta, ritorna reply + fonti.
- **Endpoint** `POST /api/chat`: usa il `session_id` **dentro il token** (non un
  input arbitrario del client), applica rate limit e ritorna `{reply, sources}`.

---

## 2. Decisioni tecniche

- **`answer()` disaccoppiato dal DB.** Riceve una `search_fn`, non la connessione:
  così l'intera orchestrazione (RAG + storia + LLM) è testabile offline con fake.
- **session_id dal token firmato.** La storia è legata alla sessione emessa dal
  backend; il client non può spacciarsi per un'altra conversazione.
- **TTL sulle conversazioni.** Coerente col GDPR: i dati delle chat non si
  accumulano, spariscono da soli.
- **Grounding di base ora, system prompt "definitivo" al Passo 7.** Le regole
  anti-allucinazione complete + i dati/calcoli deterministici (prezzi, orari,
  conversioni °C↔K) sono il cuore del Passo 7; qui c'è la struttura del prompt.

---

## 3. Verifica

`pytest` → **74 passed**. Nuovi (14): store sessioni in-memory (trim, isolamento)
e Redis (con fake client: rpush/ltrim/expire/lrange), adapter LLM (Stub +
Ollama con trasporto finto), orchestrazione `answer()` (fonti, storia, grounding),
endpoint `/api/chat` e `/api/rooms` con TestClient (200, 404, 401, 422).

**Da fare (runtime):** con Docker + Redis + un modello (Ollama `llama3`),
provare `POST /api/session` → `POST /api/chat` e verificare che l'IA risponda
**solo** dai dati del tenant.

---

## 4. Prossimo passo

**Passo 7 — governance delle risposte.** Rifinire il system prompt con le regole
complete anti-allucinazione ed esempi; spostare nel backend i **dati/calcoli
deterministici** (prezzi, orari, conversioni) così l'IA li riporta soltanto;
distinguere i dati stanza (precisi, da `rooms`) dalle schede descrittive (RAG).
