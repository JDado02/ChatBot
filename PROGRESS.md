# PROGRESS — AI Concierge

**Ultimo aggiornamento:** 2026-07-01
**Fase attuale:** Setup del flusso di lavoro completato. Nessun codice applicativo ancora scritto.

> Questo file è il **segnalibro** del progetto. Per riprendere una sessione: leggi questo file, poi guarda l'ultimo commit git. Non serve altro.

## Stato in breve

- Repo con la documentazione di architettura ([AI_Concierge_Contesto_Progetto.md](AI_Concierge_Contesto_Progetto.md)) + file di workflow ([CLAUDE.md](CLAUDE.md), questo file).
- **In attesa del "via" dell'utente** per iniziare l'implementazione (Passo 1).

## Roadmap (sez. 14 del documento di architettura)

- [ ] **1.** Ambiente locale con Docker Compose: PostgreSQL + pgvector + Redis
- [ ] **2.** Attivare RLS sulle tabelle + test isolamento tra 2 hotel fittizi e sessioni simultanee
- [ ] **3.** Dati di test: 30 stanze fittizie (con JSONB) + knowledge base d'esempio
- [ ] **4.** Pipeline di embedding (modello locale) + ricerca semantica con pgvector
- [ ] **5.** Sicurezza widget: allowlist domini + rate limiting + token di sessione
- [ ] **6.** Endpoint FastAPI: chat, sessioni Redis, RAG sulla knowledge base, lettura stanze
- [ ] **7.** System prompt: regole di risposta + dati/calcoli deterministici (prezzi, orari, conversioni)
- [ ] **8.** Function calling: richiesta prenotazione (email reception) + adapter PMS del primo hotel
- [ ] **9.** Server GPU dedicato EU (noleggio iniziale) con vLLM

## Prossimo passo

**Passo 1** — ambiente Docker locale (PostgreSQL + pgvector, Redis). In attesa del via dell'utente.

## Decisioni prese

- **2026-07-01** — Flusso di lavoro a **singolo agente**, "autonomia a blocchi" (un passo della roadmap alla volta), **no multi-agente**. Motivo: budget token (piano Pro) e coerenza sui vincoli trasversali (RLS, GDPR, multi-tenant). Stato tracciato in `PROGRESS.md` + commit piccoli e frequenti.

## Note / questioni aperte

- _(nessuna per ora)_
