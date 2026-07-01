# 02 — Dati di test ricchi (seed) + robustezza privilegi

**Data:** 2026-07-01
**Stato:** ✅ Scritto e validato staticamente — ⚠️ da caricare al primo avvio Docker (vedi §4)
**Corrisponde a:** Passo 3 della roadmap (30 stanze con JSONB + knowledge base d'esempio)

> Questo documento registra l'ampliamento dei dati di test da un seed minimo (per il solo test di isolamento) a un dataset ricco e realistico, utile anche per la successiva pipeline di embedding + ricerca semantica (Passo 4).

---

## 1. Cosa è stato realizzato

1. **30 stanze per `hotel_alpha`** in `db/init/02_seed.sql`, generate come **6 archetipi × 5 piani** (camere `101`–`106`, `201`–`206`, … `501`–`506`).
   - Tutti e tre i campi JSONB ora popolati: `air_conditioning`, `refrigerator` e **`view_and_exposure`** (prima non valorizzato).
   - Varietà realistica: la **vista cambia con il piano** (piani 4–5 → "Vista mare", piano 1 → "Vista giardino", intermedi → "Vista città"); esposizione, balcone e dotazioni (`amenities`) variano per archetipo.
   - Tipologie: Singola Comfort, Doppia Standard, Doppia Deluxe, Tripla Familiare, Suite Junior, Suite Panoramica.
2. **Knowledge base ricca per `hotel_alpha`**: 14 schede realistiche su categorie diverse — `ristorante`, `colazione`, `servizi` (reception, Wi-Fi, parcheggio, room service/lavanderia), `wellness`, `strutture`, `policy` (cancellazione, animali, famiglie), `indicazioni`, `dintorni`, `eventi`. Ogni scheda ha `content` descrittivo + `metadata` strutturato.
3. **`hotel_beta` piccolo** (2 stanze + 2 schede): serve come contrasto per l'isolamento multi-tenant e per verificare che un tenant non veda l'altro.
4. **Miglioramento di robustezza in `01_schema.sql`**: aggiunto `ALTER DEFAULT PRIVILEGES` così le tabelle/sequenze **create in futuro** (es. migrazioni del Passo 6) sono automaticamente accessibili ad `app_user`, senza dover rifare la GRANT ogni volta.

---

## 2. Decisioni tecniche

### 2.1 Generazione via `CROSS JOIN` invece di 30 INSERT a mano
Le 30 stanze nascono da una CTE `archetipi` (6 righe) in `CROSS JOIN` con `generate_series(1,5)` (i piani). Vantaggi: file compatto e leggibile, varietà controllata, facile da estendere. Il `room_number` è calcolato come `piano*100 + posizione` e castato a testo.

### 2.2 `view_and_exposure` calcolato dal piano
La vista è derivata dal numero di piano con un `CASE`, così i dati sono coerenti (più sali, migliore la vista) e non ripetitivi. `balcone` è un booleano JSON derivato da piano/archetipo.

### 2.3 `embedding` resta NULL
Come nel seed precedente, l'`embedding vector(1024)` non è popolato qui: lo genera la pipeline del Passo 4 con il modello locale. L'indice HNSW ignora i NULL, quindi nessun impatto finché non ci sono embedding.

---

## 3. Verifica (senza Docker)

Su questa macchina il backend Linux di Docker Desktop non era avviabile (WSL2 senza distribuzioni), quindi il seed **non è stato caricato a runtime qui**. È stato però **validato staticamente**:

- **Apici bilanciati**: nessun apostrofo italiano non-escapato (ogni riga ha un numero pari di `'`).
- **Grammatica PostgreSQL reale** (parser `pglast`/libpg_query):
  - `01_schema.sql` → 19 statement validi (incl. `ALTER DEFAULT PRIVILEGES`);
  - `02_seed.sql` → 5 statement validi.

I Passi 1–2 erano già stati verificati a runtime sull'altro computer (test isolamento 4/4 PASS, vedi [01_setup_docker_database.md](01_setup_docker_database.md)).

---

## 4. ⚠️ Come caricare il nuovo seed

Gli script in `db/init/` girano **solo al primo avvio**, quando il volume dati è vuoto. Se il DB è già stato inizializzato con il vecchio seed, bisogna **ricreare il volume**:

```bash
docker compose down -v        # cancella i dati esistenti
docker compose up -d          # re-init: ricrea schema + carica il nuovo seed
docker compose ps             # attendere "healthy"
./db/test/run_isolation_test.sh   # atteso: 4x PASS (i conteggi ora sono più alti)
```

> Il test di isolamento non ha conteggi hard-coded (usa "il mio tenant > 0 e gli altri = 0"), quindi continua a passare anche con 30 stanze.

---

## 5. Prossimo passo

**Passo 4:** pipeline di **embedding** (modello locale, es. bge-m3 / multilingual-e5 via Ollama in dev) per popolare `knowledge_base.embedding`, e **ricerca semantica** con pgvector (distanza coseno, indice HNSW) per il RAG.
