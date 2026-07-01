# 08 — Prenotazioni + adapter PMS (function calling)

**Data:** 2026-07-01
**Stato:** ✅ Parte codificabile completa e testata (offline). ⚠️ Connettore PMS reale e SMTP reale = su misura/infra (fuori dall'autonomia)
**Corrisponde a:** Passo 8 della roadmap (parziale)

> Il chatbot raccoglie una **richiesta** di prenotazione (non una conferma) e la
> gira alla reception via email. Più l'interfaccia comune verso il gestionale (PMS).

---

## 1. Cosa è stato realizzato

- **`app/booking.py`** — `BookingInput`, `validate_booking` (nome, email, ospiti,
  date coerenti via `calc.nights_between`), `create_booking` (INSERT in
  `booking_requests` con stato `pending`, via `tenant_transaction` → RLS).
- **`app/email.py`** — adapter `EmailSender`: `StubEmailSender` (registra, dev/test)
  e `SmtpEmailSender` (reale); `format_booking_email` (oggetto + corpo con notti).
- **`app/pms.py`** — interfaccia `PMSAdapter` (`get_availability`, `get_price`) +
  `NullPMS` (nessuna automazione → "verifichiamo e la ricontattiamo") e `FakePMS`.
- **DB** — colonna `reception_email` in `tenants` + seed; `get_tenant_contact`.
- **Endpoint** `POST /api/booking` — token richiesto, rate limit, validazione;
  salva la richiesta e invia l'email alla reception; risposta chiara ("richiesta
  inviata, riceverai conferma via email").

---

## 2. Decisioni tecniche

- **Richiesta, non conferma.** Stato `pending`; la reception conferma via email.
  Il messaggio all'utente lo dice esplicitamente (niente false aspettative).
- **Adapter email e PMS.** Come per LLM/embedding: interfaccia stabile, connettore
  sostituibile. Il PMS reale è **su misura per ogni hotel** (API / channel manager
  / file / manuale) e si scrive col cliente; qui c'è l'interfaccia + fake.
- **`None` = "non so"** nel PMS: modella il caso "nessuna automazione" senza dare
  numeri sbagliati (coerente con l'anti-allucinazione).
- **RLS anche in scrittura.** L'INSERT passa da `tenant_transaction`; la policy
  `WITH CHECK` impedisce di creare richieste per un altro hotel.

---

## 3. Verifica

`pytest` → **98 passed** (11 nuovi): validazione (email, ospiti, date invertite),
`create_booking` con connessione finta (verifica INSERT + tenant come primo
parametro), `format_booking_email`, `StubEmailSender`, PMS fake/null, endpoint
`/api/booking` (200 con `booking_id`+`pending`, 422 validazione, 401 senza token).
SQL nuovi validati con `pglast`.

---

## 4. Cosa resta (fuori dall'autonomia / infra)

- **LLM function calling**: far sì che sia il modello, in conversazione, a
  raccogliere i dati e invocare `create_booking` (serve il modello attivo).
- **SMTP reale**: configurare un servizio email EU (host/porta/credenziali via env)
  e usare `SmtpEmailSender` al posto dello stub.
- **Connettore PMS del primo hotel reale**: da scrivere col cliente in sopralluogo.
- **Passo 9**: server GPU dedicato EU (noleggio) con vLLM — scelta d'infrastruttura,
  richiede decisioni dell'utente (provider, budget).
