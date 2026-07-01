# CLAUDE.md

Guida per Claude Code su questo repository. Questo file viene letto **automaticamente** all'inizio di ogni sessione: contiene solo cose stabili (architettura, regole, flusso). Lo stato di avanzamento vive in `PROGRESS.md`.

## Cos'è il progetto

AI Concierge — un chatbot SaaS **multi-tenant** (caso d'uso principale: hotel), **self-hosted in Europa** per conformità GDPR. La fonte di verità per ogni decisione di design è [docs/AI_Concierge_Contesto_Progetto.md](docs/AI_Concierge_Contesto_Progetto.md). Leggila prima di implementare parti nuove.

## Mappa dei file (dove sta cosa)

- **`CLAUDE.md`** (questo) — regole e vincoli, auto-caricato a ogni sessione. Solo cose stabili.
- **`PROGRESS.md`** — il **segnalibro**: roadmap, stato attuale, prossimo passo, decisioni. Leggilo per primo.
- **`README.md`** — panoramica pubblica del progetto + come avviarlo. Da aggiornare quando cambia lo stato.
- **`docs/`** — documento di architettura + un **report tecnico per ogni passo** completato (`docs/0N_*.md`).

## Flusso di lavoro (IMPORTANTE)

Il vincolo reale è il **budget token** (piano Claude Pro). Obiettivo: ogni sessione deve poter ripartire da zero leggendo i file del repo, **senza rispiegazioni a voce**.

1. **A inizio sessione:** leggi prima `PROGRESS.md`. Dice dove siamo e qual è il prossimo passo.
2. **Un blocco alla volta:** un **singolo passo della roadmap** per volta, in autonomia, fino a completarlo. Un solo agente in sequenza — niente sciami di agenti in parallelo (bruciano token e rischiano incoerenza sui vincoli trasversali).
3. **Commit piccoli e frequenti**, messaggio chiaro. _Ultimo commit + `PROGRESS.md` = il segnalibro._
4. **Alla fine di ogni passo:** aggiorna `PROGRESS.md` (stato + prossimo passo + decisioni), aggiorna `README.md` se lo stato è cambiato, e scrivi un breve **report in `docs/0N_*.md`**. Fallo **prima** di finire i token, non dopo. Ricordalo tu stesso all'utente quando la sessione si allunga.
5. **Autonomia + verifica:** completi il blocco da solo, poi l'utente analizza, testa e chiede le modifiche.

## Vincoli architetturali da non violare mai

- **GDPR:** nessuna IA o servizio USA (no OpenAI). Tutto self-hosted in EU. Dati utente elaborati in memoria, **mai** salvati o usati per training.
- **Multi-tenancy:** ogni tabella ha `tenant_id` + **Row-Level Security** PostgreSQL. Il backend si connette come ruolo **non-superuser `app_user`** (i superuser bypassano la RLS). Identità impostata con `SET LOCAL app.current_tenant` **dentro ogni transazione** (mai a livello di connessione, per via del connection pooling).
- **Anti-allucinazione:** l'IA risponde **solo** dai dati forniti. Numeri, prezzi, orari e conversioni li calcola il **backend**, mai l'IA; l'IA li riporta soltanto.
- **Sicurezza widget:** la API key è **pubblica** (identifica, non protegge). Difese vere: allowlist domini (Origin/Referer) + rate limiting + token di sessione a vita breve.

## Stack

Backend **Python 3.11 + FastAPI** (async) · **PostgreSQL 16 + pgvector** · **Redis 7** (sessioni, TTL) · **vLLM** (prod) / **Ollama** (dev), Llama 3 8B / Mistral 7B · embedding locale (bge-m3 / multilingual-e5, dim. 1024) · Widget **Vanilla JS + Shadow DOM** · **Docker Compose** · **Caddy** (HTTPS).

## Comandi

```bash
cp .env.example .env               # (prima volta) config locale
docker compose up -d               # avvia Postgres+pgvector e Redis
docker compose ps                  # stato container (attendere "healthy")
./db/test/run_isolation_test.sh    # test isolamento RLS (atteso: 4x PASS)
docker compose down                # ferma (i dati restano nel volume)
docker compose down -v             # ferma E cancella i dati (re-init da zero)
```

> Gli script in `db/init/` girano **solo al primo avvio** (volume vuoto). Dopo modifiche a schema/seed: `docker compose down -v && docker compose up -d`.

## Lingua

Progetto e comunicazione in **italiano**.
