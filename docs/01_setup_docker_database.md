# 01 — Setup ambiente locale: Docker + Database

**Data:** 18 Giugno 2026
**Stato:** ✅ Completato e verificato
**Corrisponde a:** Prossimi Passi punti 1 e 2 del documento di contesto (`AI_Concierge_Contesto_Progetto.md`)

> Questo documento registra cosa è stato fatto nella prima fase di sviluppo: l'ambiente locale con PostgreSQL+pgvector e Redis via Docker, lo schema del database con la multi-tenancy (RLS), i dati di test e la verifica dell'isolamento tra hotel.

---

## 1. Cosa è stato realizzato

1. **Ambiente locale containerizzato** con Docker Compose: PostgreSQL 16 (con pgvector) + Redis 7.
2. **Schema del database** completo: le tre tabelle del progetto (`rooms`, `knowledge_base`, `booking_requests`).
3. **Multi-tenancy con Row-Level Security (RLS)**: il database stesso impedisce a un hotel di vedere i dati di un altro.
4. **Ruolo applicativo non-superuser** (`app_user`): il backend si connetterà con questo, perché i superuser bypassano la RLS.
5. **Dati di test**: due hotel fittizi (`hotel_alpha`, `hotel_beta`).
6. **Test automatico di isolamento**: 4 verifiche, tutte superate.

---

## 2. Struttura dei file creati

```
ChatBot/
├── docker-compose.yml          # Definizione servizi Postgres + Redis
├── .env                        # Config locale (password dev) — non committare
├── .env.example                # Template da copiare in .env
├── .gitignore
├── db/
│   ├── init/                   # Eseguiti UNA VOLTA al primo avvio del DB
│   │   ├── 00_create_app_role.sh   # Crea il ruolo non-superuser 'app_user'
│   │   ├── 01_schema.sql           # Estensione vector, tabelle, RLS, policy, grant
│   │   └── 02_seed.sql             # Dati di test (hotel_alpha + hotel_beta)
│   └── test/
│       ├── test_rls_isolation.sql  # Le 4 asserzioni di isolamento
│       └── run_isolation_test.sh   # Runner: esegue il test come 'app_user'
└── docs/
    └── 01_setup_docker_database.md # questo file
```

---

## 3. Decisioni tecniche e perché

### 3.1 Immagine `pgvector/pgvector:pg16`
Invece di Postgres "liscio" + compilazione manuale di pgvector, si usa l'immagine ufficiale che include già l'estensione. Basta `CREATE EXTENSION vector`.

### 3.2 Ruolo `app_user` NON-superuser — punto critico per la sicurezza
In PostgreSQL **i superuser bypassano sempre la RLS**. Se il backend si collegasse come `postgres`, l'isolamento tra hotel non verrebbe applicato e ci sarebbe rischio di fuga dati. Per questo:
- Il superuser `postgres` serve solo per init/migrazioni/seed.
- Il backend si connette come `app_user` (login, niente superuser), che è **sempre** soggetto alla RLS.

La creazione del ruolo è in uno script `.sh` (non `.sql`) perché la password arriva da una variabile d'ambiente, e gli script SQL di init non possono leggere l'ambiente del sistema operativo. Il nome del ruolo è fisso (`app_user`); solo la password è configurabile via `.env`.

### 3.3 `ENABLE` + `FORCE ROW LEVEL SECURITY`
- `ENABLE` attiva la RLS.
- `FORCE` la applica **anche al proprietario** della tabella, non solo agli altri ruoli. Senza `FORCE`, il ruolo owner vedrebbe comunque tutto.

### 3.4 Policy basata su variabile di sessione + `SET LOCAL`
La policy confronta `tenant_id` con `current_setting('app.current_tenant', true)`. Il backend, all'inizio di **ogni transazione**, esegue:
```sql
SET LOCAL app.current_tenant = '<id_hotel>';
```
`SET LOCAL` vincola l'identità alla singola transazione: non resta "attaccata" a una connessione riusata dal pool (altrimenti un hotel potrebbe ereditare il contesto di un altro). Il secondo argomento `true` di `current_setting` evita errori se la variabile non è impostata: in quel caso ritorna NULL e **non si vede nulla** (comportamento fail-safe).

### 3.5 `WITH CHECK` oltre a `USING`
- `USING` filtra le righe in **lettura** (e quali si possono aggiornare/cancellare).
- `WITH CHECK` blocca le **scritture** verso un tenant diverso dal proprio. Così un hotel non può nemmeno inserire righe a nome di un altro.

### 3.6 Embedding lasciati NULL nel seed
Il campo `embedding vector(1024)` (dimensione di bge-m3 / multilingual-e5) viene popolato dalla pipeline applicativa con il modello locale, nel passo successivo. Per testare l'isolamento non serve.

---

## 4. Come avviare l'ambiente

```bash
# 1. (prima volta) copia il template e personalizza se vuoi
cp .env.example .env

# 2. avvia i container
docker compose up -d

# 3. verifica lo stato (devono essere "healthy")
docker compose ps
```

Connessioni:
- **Postgres** → `localhost:5432`, db `concierge`, ruolo backend `app_user`.
- **Redis** → `localhost:6379`.

### Comandi utili
```bash
docker compose logs postgres        # log init/runtime
docker compose down                 # ferma i container (i dati restano nel volume)
docker compose down -v              # ferma E CANCELLA i dati (per re-inizializzare da zero)
```

> ⚠️ **Importante:** gli script in `db/init/` girano **solo al primo avvio**, quando il volume dati è vuoto. Se modifichi schema o seed, devi ricreare il volume con `docker compose down -v && docker compose up -d`.

---

## 5. Come eseguire il test di isolamento

```bash
./db/test/run_isolation_test.sh
```

Il test si connette **come `app_user`** (non come superuser) ed esegue 4 verifiche:

| # | Verifica | Esito atteso |
|---|---|---|
| 1 | Nessun tenant impostato | 0 righe visibili (fail-safe) |
| 2 | `tenant = hotel_alpha` | Vede solo stanze di alpha, 0 di altri |
| 3 | `tenant = hotel_beta` | Vede solo schede di beta, 0 di altri |
| 4 | Insert cross-tenant | Rifiutato dal database |

### Risultato dell'esecuzione (18 Giu 2026)
```
== Conferma: NON dobbiamo essere superuser ==
 app_user | rolsuper = f
TEST 1: PASS — senza tenant vedo 0 stanze
TEST 2: PASS — vedo 2 stanze alpha, 0 di altri hotel
TEST 3: PASS — vedo 1 schede beta, 0 di altri hotel
TEST 4: PASS — insert cross-tenant correttamente rifiutato
== TUTTI I TEST SUPERATI ==
```

Anche Redis è stato verificato: risponde `PONG` e gestisce correttamente le chiavi con TTL (es. `hotel_alpha:sess-001` con scadenza a 60s), come previsto per la memoria delle conversazioni.

---

## 6. Note di sicurezza / produzione

- Le password in `.env` sono **solo per sviluppo locale**. In produzione: password forti, segrete, fuori dal repository (il `.gitignore` esclude già `.env`).
- In produzione valutare anche: connessioni TLS verso Postgres, backup automatici e piano di ripristino (cfr. sez. 13 del documento di contesto — singolo server = singolo punto di rottura).

---

## 7. Prossimo passo

Il punto 2 dei Prossimi Passi è completato (RLS attiva e isolamento verificato). Il prossimo:

> **Punto 3–4:** popolare dati di test più ricchi (30 stanze fittizie con JSONB + knowledge base d'esempio) e implementare la **pipeline di embedding** (modello locale) con la **ricerca semantica** via pgvector.
