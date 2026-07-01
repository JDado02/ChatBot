# Widget "Aria" — chat concierge embeddabile

Widget di chat che l'hotel integra nel proprio sito. **Vanilla JS + Shadow DOM**,
**zero dipendenze** e **nessuna risorsa esterna** (font/CDN): tutto self-contained,
coerente con la privacy GDPR-first del progetto.

- Isolato dal CSS del sito ospite (Shadow DOM).
- Branding **Aria**: palette midnight + oro, campanello da concierge.
- Launcher flottante → pannello con saluto, suggerimenti, chat.
- Parla con l'API: `POST /api/session` → token → `POST /api/chat`.
- Persistenza conversazione in `sessionStorage` (si azzera con la scheda).
- Accessibile (ruoli ARIA, tastiera: Invio invia, Esc chiude) e responsive (mobile a schermo intero).

## Integrazione (sul sito dell'hotel)

```html
<script src="https://cdn.tuodominio.eu/widget.js"
        data-api-url="https://api.tuodominio.eu"
        data-api-key="pk_alpha_dev_0001"
        data-hotel-name="Hotel Alpha"
        data-assistant-name="Aria"
        data-accent="#D9A441"
        defer></script>
```

In alternativa alle `data-*` si può usare `window.AriaConfig = { ... }` **prima**
di caricare lo script (utile per config dinamica).

### Opzioni

| data-* / AriaConfig | Default | Descrizione |
|---|---|---|
| `api-url` / `apiUrl` | `http://localhost:8000` | Base URL del backend |
| `api-key` / `apiKey` | — | API key pubblica del tenant |
| `hotel-name` / `hotelName` | "il nostro hotel" | Nome usato nel saluto |
| `assistant-name` / `assistantName` | `Aria` | Nome dell'assistente |
| `accent` | `#D9A441` | Colore d'accento (oro) |
| `position` | `right` | `right` \| `left` |
| `demo` | `false` | `true` = risposte simulate, senza backend |
| `greeting` | (auto) | Messaggio di benvenuto personalizzato |

## Provarlo in locale

La pagina [`index.html`](index.html) simula il sito di un hotel con il widget.

```bash
# dalla radice del progetto: servi la cartella widget/
python -m http.server 5500 --directory widget
# apri http://localhost:5500
```

- **Modalità DEMO** (default): risposte simulate, funziona **senza backend** —
  ideale per vedere subito grafica e conversazione.
- **Modalità LIVE** (`http://localhost:5500/?mode=live`): usa l'API reale su
  `localhost:8000`. Richiede il backend attivo (`uvicorn app.api.main:app`) e,
  per risposte vere, **Ollama** con i modelli. Senza modello, `/api/chat` risponde
  503 e il widget mostra un messaggio d'errore cortese (comportamento verificato).

> Origini di test: la pagina usa la chiave `pk_alpha_dev_0001`; `localhost` è tra
> i domini autorizzati nel seed, quindi `/api/session` va a buon fine.

## Note di sicurezza / privacy

- L'API key è **pubblica** (identifica il tenant). Le difese vere sono lato
  server: allowlist domini + rate limiting + token di sessione a vita breve.
- Il widget non carica risorse di terze parti e non usa cookie: solo
  `sessionStorage` per token e storia (cancellati alla chiusura della scheda).
- L'input dell'utente viene sempre **escapato** prima del rendering (niente XSS).

## Personalizzazione grafica

I colori sono variabili CSS nel Shadow DOM. Per il colore d'accento basta
`data-accent`. Per un restyle più profondo (per singolo hotel) si possono
esporre altre variabili (`--ink`, `--surface`, …) in una prossima iterazione.
