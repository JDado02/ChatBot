# CLAUDE.md

Guida per Claude Code su questo repository. Questo file viene letto **automaticamente** all'inizio di ogni sessione: contiene solo cose stabili (architettura, regole, flusso). Lo stato di avanzamento vive invece in `PROGRESS.md`.

## Cos'è il progetto

AI Concierge — un chatbot SaaS **multi-tenant** (caso d'uso principale: hotel), **self-hosted in Europa** per conformità GDPR. L'architettura completa e la fonte di verità per ogni decisione di design è [AI_Concierge_Contesto_Progetto.md](AI_Concierge_Contesto_Progetto.md). Leggila prima di implementare parti nuove.

## Flusso di lavoro (IMPORTANTE)

Il vincolo reale è il **budget token** (piano Claude Pro). Obiettivo: ogni sessione deve poter ripartire da zero leggendo i file del repo, **senza rispiegazioni a voce**.

1. **A inizio sessione:** leggi sempre prima `PROGRESS.md`. Dice esattamente dove siamo e qual è il prossimo passo.
2. **Un blocco alla volta:** si lavora su un **singolo passo della roadmap** per volta, in autonomia, fino a completarlo. Un solo agente in sequenza — **niente sciami di agenti in parallelo** (bruciano token e rischiano incoerenza sui vincoli trasversali).
3. **Commit piccoli e frequenti:** ogni pezzo funzionante va committato con messaggio chiaro. _Ultimo commit + `PROGRESS.md` = il segnalibro._
4. **Aggiorna `PROGRESS.md` PRIMA di finire i token,** non dopo. Alla fine di ogni blocco (o quando la sessione si allunga) aggiorna: stato, prossimo passo, decisioni prese. Ricordalo tu stesso all'utente quando la sessione diventa lunga.
5. **Autonomia + verifica:** completi il blocco da solo, poi l'utente analizza, testa e chiede le modifiche.

## Vincoli architetturali da non violare mai

- **GDPR:** nessuna IA o servizio USA (no OpenAI). Tutto self-hosted in EU. Dati utente elaborati in memoria, **mai** salvati o usati per training.
- **Multi-tenancy:** ogni tabella ha `tenant_id` + **Row-Level Security** PostgreSQL. Identità impostata con `SET LOCAL app.current_tenant` **dentro ogni transazione** (mai a livello di connessione, per via del connection pooling).
- **Anti-allucinazione:** l'IA risponde **solo** dai dati forniti. Numeri, prezzi, orari e conversioni li calcola il **backend**, mai l'IA; l'IA li riporta soltanto.
- **Sicurezza widget:** la API key è **pubblica** (identifica, non protegge). Difese vere: allowlist domini (Origin/Referer) + rate limiting + token di sessione a vita breve.

## Stack

Backend **Python 3.11 + FastAPI** (async) · **PostgreSQL + pgvector** · **Redis** (sessioni, TTL) · **vLLM** (prod) / **Ollama** (dev), Llama 3 8B / Mistral 7B · embedding locale (bge-m3 / multilingual-e5) · Widget **Vanilla JS + Shadow DOM** · **Docker Compose** · **Caddy** (HTTPS).

## Comandi

_(Da compilare quando esisterà il codice: avvio Docker Compose, test, lint, migrazioni, ecc.)_

## Lingua

Progetto e comunicazione in **italiano**.
