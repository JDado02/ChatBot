# 07 — Governance delle risposte (anti-allucinazione)

**Data:** 2026-07-01
**Stato:** ✅ Completo e testato (offline)
**Corrisponde a:** Passo 7 della roadmap

> Il punto più delicato: tenere l'IA "ancorata" ai dati. Regole sempre presenti
> nel system prompt + numeri/conversioni calcolati dal backend (mai dall'IA).

---

## 1. Cosa è stato realizzato

- **`app/calc.py`** — calcoli DETERMINISTICI: conversioni temperatura
  (°C↔K, °C→°F), `nights_between` (notti tra due date), `format_price_eur`
  (formato italiano `1.234,56 €`), `total_price`.
- **`app/prompt.py`** — `SYSTEM_PROMPT` con regole esplicite + esempio;
  `build_context` (schede RAG); `build_room_facts` (dati stanza precisi, con le
  conversioni **già calcolate**, es. 16°C → 289.15 K); `build_system_prompt`
  che unisce regole + CONTESTO + eventuali DATI STANZA.
- **`app/chat.py`** — ora usa `prompt.py` (niente duplicazione) e `answer()`
  accetta `room_facts` per iniettare i dati stanza precisi nella conversazione.

---

## 2. Le tre leve anti-allucinazione (dal documento di architettura)

1. **Regole sempre presenti** — stanno nel system prompt, riletto a ogni
   risposta. Scritte chiare, con un esempio ("se manca il prezzo, non
   inventarlo").
2. **Ancoraggio ai dati** — all'IA si danno SOLO le schede pertinenti + i dati
   stanza; istruzione esplicita a non uscire dal contesto.
3. **Numeri calcolati dal backend** — prezzi, notti e conversioni li produce
   `calc.py`; l'IA li riporta soltanto. Esempio implementato: il range del
   condizionatore in °C viene convertito in Kelvin dal sistema quando la stanza
   lo supporta, così l'IA non deve calcolarlo.

---

## 3. Verifica

`pytest` → **87 passed** (13 nuovi): conversioni esatte (0°C=273.15K,
100°C=212°F…), `nights_between` (stringhe/date, errore se date invertite),
`format_price_eur` (`15,00 €`, `1.234,50 €`), `total_price`; `build_room_facts`
con e senza Kelvin, senza climatizzatore; `build_system_prompt` con sezione
DATI STANZA.

---

## 4. Prossimo passo

**Passo 8 — function calling:**
- **Richiesta di prenotazione**: raccolta dati → salvataggio in `booking_requests`
  → email alla reception (dietro un adapter, stub in dev). `answer()` è già
  pronto a ricevere dati stanza precisi.
- **Adapter PMS**: interfaccia comune (`get_disponibilita`, `get_prezzo`) con
  connettore su misura per il primo hotel reale; risposte in cache breve su Redis.
