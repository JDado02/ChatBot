# 09 — Widget frontend "Aria"

**Data:** 2026-07-01
**Stato:** ✅ Completo e testato nel browser (demo + live)
**Corrisponde a:** il componente widget dell'architettura (Vanilla JS + Shadow DOM)

> Il pezzo che vede l'utente finale: la chat che l'hotel integra nel proprio sito.

---

## 1. Cosa è stato realizzato

- **[`widget/widget.js`](../widget/widget.js)** — widget completo, self-contained,
  ~400 righe: launcher, pannello, bolle utente/bot, avatar, fonti, suggerimenti
  iniziali, indicatore "sta scrivendo", input auto-espandibile.
- **Branding "Aria"**: identità dedicata — palette *midnight navy + oro*,
  campanello da concierge, tono cortese. Nome assistente configurabile.
- **Integrazione API**: `POST /api/session` (con API key + Origin) → token in
  `sessionStorage` → `POST /api/chat`. Retry automatico su token scaduto (401),
  messaggi cortesi su 429 (rate limit) e 503 (servizio non disponibile).
- **Persistenza**: la conversazione sopravvive al reload/navigazione
  (`sessionStorage`), si azzera alla chiusura della scheda (privacy).
- **Modalità demo**: risposte simulate (KB dell'hotel) per mostrare il widget
  senza backend.
- **[`widget/index.html`](../widget/index.html)** — pagina demo "Hotel Alpha"
  (demo | `?mode=live`).

---

## 2. Decisioni tecniche

- **Shadow DOM + zero risorse esterne.** Il widget non eredita né inquina il CSS
  del sito ospite, e non carica font/CDN di terzi: coerente con la GDPR-first
  (nessun dato dell'utente esce verso terze parti). Icone SVG inline.
- **Sicurezza del rendering.** Ogni testo (incluse le risposte) è **escapato**
  prima dell'inserimento nel DOM: niente XSS anche se il modello restituisse HTML.
- **Resilienza.** Se il backend/modello non è disponibile la chat non si rompe:
  mostra un messaggio d'errore chiaro e on-brand. Per questo, lato API, gli
  errori di irraggiungibilità del modello sono stati convertiti da 500 (senza
  CORS) a **503 con header CORS**, così il browser può leggerli.
- **Accessibilità e mobile.** Ruoli ARIA (`dialog`, `log`), gestione tastiera
  (Invio/Esc), focus; su mobile il pannello va a schermo intero; supporto a
  `prefers-reduced-motion`.

---

## 3. Verifica (browser)

Testato con il server di anteprima (`http.server` su `widget/`) via ispezione DOM
e stili computati (gli screenshot dello strumento erano intermittenti):

- **Rendering/branding**: launcher posizionato correttamente; pannello con header,
  saluto, 4 suggerimenti, input; tutti gli accenti oro corretti (`--gold` =
  `#D9A441`), avatar campanello oro su navy.
- **Conversazione (demo)**: invio → bolla utente → risposta bot con **fonti**
  (es. "Avete il parcheggio?" → prezzo + chip "Parcheggio").
- **Live (API reale)**: `/api/session` va a buon fine (token salvato); senza
  Ollama `/api/chat` dà 503 e il widget mostra *"Il servizio non è al momento
  disponibile…"*.
- **Persistenza**: dopo il reload la conversazione viene ripristinata (niente
  ri-saluto/suggerimenti).
- **Bug risolto**: le `data-*` assenti sovrascrivevano i default (→ `--gold:
  undefined`, avatar invisibile); corretto filtrando i valori non definiti.

Come provarlo: vedi [`widget/README.md`](../widget/README.md).

---

## 4. Possibili migliorie future

- Ripristino anche dello **stato d'errore** dei messaggi (ora i messaggi
  ripristinati perdono lo stile "errore").
- **Streaming** della risposta (token-by-token) quando l'LLM è attivo.
- Rendering **markdown-lite** (grassetto/elenchi/link) delle risposte, mantenendo
  l'escaping anti-XSS.
- Variabili di tema aggiuntive per un restyle completo per-hotel.
- Piccola build/minificazione per la distribuzione via CDN.
