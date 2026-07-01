# 04 — Sicurezza del widget

**Data:** 2026-07-01
**Stato:** ✅ Primitive implementate e testate (offline) — l'applicazione sulle richieste HTTP arriva col Passo 6 (FastAPI)
**Corrisponde a:** Passo 5 della roadmap

> La API key del widget è **pubblica** (identifica, non protegge). Le difese reali
> sono tre: allowlist dei domini, rate limiting, token di sessione a vita breve.
> Qui sono implementate come moduli riutilizzabili e testati; il Passo 6 le
> monterà come dependency/middleware di FastAPI.

---

## 1. Cosa è stato realizzato

**Database** — nuova tabella `tenants` (in `db/init/01_schema.sql`) + seed:
`tenant_id`, `name`, `api_key` (univoca), `allowed_domains` (TEXT[]), `active`.
È la tabella di **lookup** dall'API key al tenant.

**Backend** — pacchetto [`backend/app/security/`](../backend/app/security):
- `tenants.py` — `get_tenant_by_api_key()`: identifica il tenant dall'API key.
- `allowlist.py` — `is_origin_allowed()`: accetta solo Origin/Referer da un
  dominio autorizzato (match host esatto, case-insensitive, **fail-closed**).
- `tokens.py` — `issue_token()`/`verify_token()`: token di sessione firmati
  HMAC-SHA256 con scadenza (`exp`), senza dipendenze esterne, confronto firma a
  tempo costante.
- `ratelimit.py` — `InMemoryRateLimiter` (test/single-process) e
  `RedisRateLimiter` (produzione), finestra fissa `limit`/`window`.

**Test** — 27 nuovi unit test (totale suite: **45 passed**), tutti offline.

---

## 2. Decisioni tecniche

### 2.1 `tenants` NON è sotto la RLS per-tenant
È la tabella che, data l'API key, dice **quale** tenant siamo: va letta prima di
conoscere il tenant. Metterla sotto la policy `app.current_tenant` la renderebbe
non interrogabile (chicken-and-egg). `app_user` ha solo `SELECT` su `tenants`
(le scritture/provisioning restano al superuser): `REVOKE INSERT/UPDATE/DELETE`.

### 2.2 Token firmati senza dipendenze
Invece di aggiungere una libreria JWT, un token `<payload_b64>.<hmac_b64>` con
`exp` copre il caso d'uso (pass a vita breve legato a sessione+tenant). Clock
iniettabile (`now_ts`) → test deterministici senza "congelare" il tempo.

### 2.3 Allowlist fail-closed, senza wildcard
Match esatto dell'host. Nessun Origin/Referer o nessun dominio configurato ⇒
si nega. Un sottodominio non è autorizzato solo perché lo è il dominio padre:
scelta prudente (si può allentare in seguito se serve).

### 2.4 Rate limiter con due backend
Stessa interfaccia `allow(key)`: in-memory per dev/test, Redis (INCR+EXPIRE) per
il backend stateless multi-processo in produzione. La chiave sarà api_key e/o IP.

---

## 3. Verifica

**Fatto (offline):** `pytest` → **45 passed**. Coperti: estrazione host e
allowlist (incl. fail-closed e no-wildcard), token (roundtrip, scadenza, firma
errata, payload manomesso, malformato), rate limiter (limite, reset finestra,
chiavi indipendenti, backend Redis con fake client), mapping tenant (incl.
parametrizzazione dell'API key contro SQL injection). SQL della tabella e del
lookup validati con `pglast`.

**Da fare (runtime/Passo 6):** montare queste primitive come dependency di
FastAPI e verificarle su richieste HTTP reali (Origin di prova, chiavi, scadenze).

---

## 4. Prossimo passo

**Passo 6:** endpoint FastAPI (async) — identificazione tenant via API key +
allowlist + rate limit + emissione/verifica token come dependency; endpoint di
ricerca/chat che usa il RAG del Passo 4; gestione sessioni su Redis.
