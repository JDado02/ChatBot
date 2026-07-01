/*!
 * Aria — AI Concierge widget
 * Vanilla JS + Shadow DOM. Nessuna dipendenza esterna, nessuna risorsa remota
 * (font/CDN): tutto self-contained, coerente con la privacy GDPR-first.
 *
 * Uso (sul sito dell'hotel):
 *   <script src="https://cdn.tuodominio.eu/widget.js"
 *           data-api-url="https://api.tuodominio.eu"
 *           data-api-key="pk_alpha_dev_0001"
 *           data-hotel-name="Hotel Alpha"
 *           data-assistant-name="Aria"
 *           data-accent="#D9A441"        (opzionale)
 *           data-demo="false"            (true = risposte simulate, senza backend)
 *           defer></script>
 */
(function () {
  "use strict";

  // ---- Configurazione (dalle data-* dello <script> o da window.AriaConfig) ----
  var script = document.currentScript || (function () {
    var s = document.getElementsByTagName("script");
    return s[s.length - 1];
  })();
  var d = (script && script.dataset) || {};
  // Tiene solo i valori realmente definiti (le data-* assenti valgono undefined
  // e NON devono sovrascrivere i default).
  function defined(o) {
    var r = {};
    Object.keys(o || {}).forEach(function (k) {
      if (o[k] !== undefined && o[k] !== "") r[k] = o[k];
    });
    return r;
  }
  var fromData = defined({
    apiUrl: d.apiUrl,
    apiKey: d.apiKey,
    hotelName: d.hotelName,
    assistantName: d.assistantName,
    accent: d.accent,
    position: d.position,
    greeting: d.greeting,
    demo: d.demo === "true" ? true : d.demo === "false" ? false : undefined,
  });
  var cfg = Object.assign(
    {
      apiUrl: "http://localhost:8000",
      apiKey: "",
      hotelName: "il nostro hotel",
      assistantName: "Aria",
      accent: "#D9A441",
      position: "right", // right | left
      demo: false,
      greeting: "",
    },
    fromData,
    defined(window.AriaConfig || {})
  );

  if (!cfg.greeting) {
    cfg.greeting =
      "Ciao! 👋 Sono " + cfg.assistantName + ", il concierge digitale di " +
      cfg.hotelName + ". Come posso aiutarti? Posso darti informazioni su camere, " +
      "orari e servizi, oppure raccogliere una richiesta di prenotazione.";
  }

  var SUGGESTIONS = [
    "A che ora è la colazione?",
    "Come funziona il check-in?",
    "Avete il parcheggio?",
    "Vorrei prenotare una camera",
  ];

  // --------------------------------- Icone (SVG inline) ---------------------------------
  var ICON_BELL =
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<path d="M12 3a1 1 0 0 1 1 1v.6a6 6 0 0 1 5 5.9v3l1.4 2.3a1 1 0 0 1-.86 1.5H5.46a1 1 0 0 1-.86-1.5L6 13.5v-3a6 6 0 0 1 5-5.9V4a1 1 0 0 1 1-1Z" fill="currentColor"/>' +
    '<path d="M9.5 19a2.5 2.5 0 0 0 5 0" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>' +
    "</svg>";
  var ICON_SEND =
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 12 20 4l-4 16-4-7-8-1Z" fill="currentColor"/></svg>';
  var ICON_CLOSE =
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  var ICON_CHAT =
    '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H9l-4 4v-4H6a2 2 0 0 1-2-2V5Z" fill="currentColor"/></svg>';

  // --------------------------------- Stili (Shadow DOM) ---------------------------------
  var CSS = `
  :host { all: initial; }
  *, *::before, *::after { box-sizing: border-box; }
  .aria-root {
    --ink: #14213D; --ink-2: #1E2A4A; --gold: ${cfg.accent}; --gold-soft: #F1DFB8;
    --surface: #FBFAF8; --bot: #FFFFFF; --muted: #6B7280; --line: #ECE9E3;
    --shadow: 0 18px 50px -12px rgba(20,33,61,.35);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: var(--ink);
    position: fixed; bottom: 24px; ${cfg.position === "left" ? "left" : "right"}: 24px;
    z-index: 2147483000;
  }

  /* Launcher */
  .aria-launcher {
    width: 62px; height: 62px; border-radius: 50%; border: none; cursor: pointer;
    background: linear-gradient(150deg, var(--ink-2), var(--ink));
    color: var(--gold); display: grid; place-items: center;
    box-shadow: var(--shadow); position: relative; transition: transform .2s ease, box-shadow .2s ease;
  }
  .aria-launcher:hover { transform: translateY(-2px) scale(1.03); }
  .aria-launcher:focus-visible { outline: 3px solid var(--gold); outline-offset: 3px; }
  .aria-launcher svg { width: 30px; height: 30px; }
  .aria-launcher::after {
    content: ""; position: absolute; inset: -4px; border-radius: 50%;
    border: 2px solid var(--gold); opacity: .0; animation: aria-pulse 2.6s ease-out 1s 3;
  }
  @keyframes aria-pulse { 0% { opacity:.5; transform: scale(1);} 100% { opacity:0; transform: scale(1.25);} }

  /* Pannello */
  .aria-panel {
    position: absolute; bottom: 78px; ${cfg.position === "left" ? "left" : "right"}: 0;
    width: 384px; max-width: calc(100vw - 32px); height: min(624px, calc(100vh - 120px));
    background: var(--surface); border-radius: 20px; box-shadow: var(--shadow);
    display: flex; flex-direction: column; overflow: hidden; transform-origin: bottom ${cfg.position};
    opacity: 0; transform: translateY(12px) scale(.98); pointer-events: none;
    transition: opacity .22s ease, transform .22s ease; border: 1px solid var(--line);
  }
  .aria-root.open .aria-panel { opacity: 1; transform: translateY(0) scale(1); pointer-events: auto; }
  .aria-root.open .aria-launcher { transform: scale(.9); opacity: .0; pointer-events: none; }

  /* Header */
  .aria-header {
    background: linear-gradient(135deg, var(--ink-2), var(--ink));
    color: #fff; padding: 16px 16px 18px; display: flex; align-items: center; gap: 12px;
    border-bottom: 2px solid var(--gold); position: relative;
  }
  .aria-badge {
    width: 42px; height: 42px; border-radius: 12px; flex: 0 0 auto; display: grid; place-items: center;
    background: rgba(217,164,65,.16); color: var(--gold); box-shadow: inset 0 0 0 1px rgba(217,164,65,.4);
  }
  .aria-badge svg { width: 24px; height: 24px; }
  .aria-htext { flex: 1 1 auto; min-width: 0; }
  .aria-title { font-size: 16px; font-weight: 700; letter-spacing: .2px; }
  .aria-status { font-size: 12px; opacity: .82; display: flex; align-items: center; gap: 6px; margin-top: 2px; }
  .aria-dot { width: 7px; height: 7px; border-radius: 50%; background: #46D39A; box-shadow: 0 0 0 3px rgba(70,211,154,.25); }
  .aria-x {
    background: rgba(255,255,255,.12); border: none; color: #fff; width: 32px; height: 32px;
    border-radius: 9px; cursor: pointer; display: grid; place-items: center; transition: background .15s;
  }
  .aria-x:hover { background: rgba(255,255,255,.24); }
  .aria-x svg { width: 18px; height: 18px; }

  /* Messaggi */
  .aria-body { flex: 1 1 auto; overflow-y: auto; padding: 18px 16px 8px; background:
    radial-gradient(120% 60% at 100% 0%, #F4F1EA 0%, var(--surface) 60%); }
  .aria-body::-webkit-scrollbar { width: 8px; }
  .aria-body::-webkit-scrollbar-thumb { background: #DED9CF; border-radius: 8px; }
  .aria-msg { display: flex; gap: 8px; margin-bottom: 14px; animation: aria-in .25s ease both; }
  @keyframes aria-in { from { opacity: 0; transform: translateY(6px);} to { opacity:1; transform:none;} }
  .aria-msg .av {
    width: 28px; height: 28px; border-radius: 8px; flex: 0 0 auto; display: grid; place-items: center;
    background: var(--ink); color: var(--gold); margin-top: 2px;
  }
  .aria-msg .av svg { width: 16px; height: 16px; }
  .aria-bubble {
    max-width: 78%; padding: 10px 13px; border-radius: 14px; font-size: 14.5px; line-height: 1.5;
    white-space: pre-wrap; word-wrap: break-word;
  }
  .aria-msg.bot .aria-bubble { background: var(--bot); border: 1px solid var(--line); border-top-left-radius: 4px; box-shadow: 0 1px 2px rgba(20,33,61,.04); }
  .aria-msg.user { flex-direction: row-reverse; }
  .aria-msg.user .aria-bubble { background: linear-gradient(135deg, var(--ink-2), var(--ink)); color: #fff; border-top-right-radius: 4px; }
  .aria-sources { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
  .aria-chip {
    font-size: 11.5px; padding: 3px 9px; border-radius: 999px; background: var(--gold-soft);
    color: #7A5B14; border: 1px solid rgba(217,164,65,.45); cursor: default;
  }

  /* Suggerimenti iniziali */
  .aria-suggest { display: flex; flex-wrap: wrap; gap: 8px; padding: 2px 4px 12px 44px; }
  .aria-suggest button {
    font: inherit; font-size: 13px; color: var(--ink); background: #fff; border: 1px solid var(--line);
    padding: 8px 12px; border-radius: 999px; cursor: pointer; transition: border-color .15s, transform .1s;
  }
  .aria-suggest button:hover { border-color: var(--gold); transform: translateY(-1px); }

  /* Typing */
  .aria-typing .aria-bubble { display: inline-flex; gap: 4px; align-items: center; }
  .aria-typing i { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); opacity: .5; animation: aria-blink 1.2s infinite; }
  .aria-typing i:nth-child(2){ animation-delay:.2s } .aria-typing i:nth-child(3){ animation-delay:.4s }
  @keyframes aria-blink { 0%,60%,100%{ transform: translateY(0); opacity:.4 } 30%{ transform: translateY(-4px); opacity:1 } }

  /* Input */
  .aria-foot { padding: 10px 12px 12px; background: var(--surface); border-top: 1px solid var(--line); }
  .aria-inputrow {
    display: flex; align-items: flex-end; gap: 8px; background: #fff; border: 1.5px solid var(--line);
    border-radius: 16px; padding: 6px 6px 6px 14px; transition: border-color .15s;
  }
  .aria-inputrow:focus-within { border-color: var(--gold); }
  .aria-input {
    flex: 1 1 auto; border: none; outline: none; resize: none; font: inherit; font-size: 14.5px;
    line-height: 1.4; max-height: 96px; padding: 6px 0; background: transparent; color: var(--ink);
  }
  .aria-send {
    flex: 0 0 auto; width: 38px; height: 38px; border-radius: 12px; border: none; cursor: pointer;
    background: linear-gradient(135deg, #E9BE63, var(--gold)); color: var(--ink); display: grid; place-items: center;
    transition: transform .12s, opacity .15s;
  }
  .aria-send:hover { transform: scale(1.06); } .aria-send:disabled { opacity: .45; cursor: default; transform: none; }
  .aria-send svg { width: 20px; height: 20px; }
  .aria-disclaimer { text-align: center; font-size: 11px; color: var(--muted); margin-top: 8px; line-height: 1.4; }
  .aria-disclaimer b { color: var(--ink); font-weight: 600; }
  .aria-powered { margin-top: 4px; opacity: .8; }
  .aria-err { color: #B4232A; }

  /* Mobile */
  @media (max-width: 480px) {
    .aria-root { bottom: 0; right: 0; left: 0; }
    .aria-panel { bottom: 0; right: 0; left: 0; width: 100vw; max-width: 100vw; height: 100vh; border-radius: 0; }
    .aria-launcher { position: fixed; bottom: 18px; ${cfg.position === "left" ? "left" : "right"}: 18px; }
  }
  @media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
  `;

  // --------------------------------- Costruzione DOM ---------------------------------
  var host = document.createElement("div");
  host.setAttribute("aria-live", "polite");
  document.body.appendChild(host);
  var root = host.attachShadow({ mode: "open" });

  var wrap = document.createElement("div");
  wrap.className = "aria-root";
  wrap.innerHTML =
    '<style>' + CSS + '</style>' +
    '<button class="aria-launcher" aria-label="Apri la chat con ' + esc(cfg.assistantName) + '">' + ICON_CHAT + '</button>' +
    '<section class="aria-panel" role="dialog" aria-label="Chat con ' + esc(cfg.assistantName) + '" aria-modal="false">' +
      '<header class="aria-header">' +
        '<div class="aria-badge">' + ICON_BELL + '</div>' +
        '<div class="aria-htext">' +
          '<div class="aria-title">' + esc(cfg.assistantName) + '</div>' +
          '<div class="aria-status"><span class="aria-dot"></span> Concierge · online</div>' +
        '</div>' +
        '<button class="aria-x" aria-label="Chiudi la chat">' + ICON_CLOSE + '</button>' +
      '</header>' +
      '<div class="aria-body" role="log" aria-live="polite"></div>' +
      '<div class="aria-foot">' +
        '<div class="aria-inputrow">' +
          '<textarea class="aria-input" rows="1" placeholder="Scrivi un messaggio…" aria-label="Messaggio"></textarea>' +
          '<button class="aria-send" aria-label="Invia" disabled>' + ICON_SEND + '</button>' +
        '</div>' +
        '<div class="aria-disclaimer">' + esc(cfg.assistantName) + ' può commettere errori. Le prenotazioni sono <b>richieste</b>, confermate dalla reception.' +
        '<div class="aria-powered">Powered by AI Concierge</div></div>' +
      '</div>' +
    '</section>';
  root.appendChild(wrap);

  var el = {
    launcher: root.querySelector(".aria-launcher"),
    panel: root.querySelector(".aria-panel"),
    close: root.querySelector(".aria-x"),
    body: root.querySelector(".aria-body"),
    input: root.querySelector(".aria-input"),
    send: root.querySelector(".aria-send"),
  };

  // --------------------------------- Stato ---------------------------------
  var state = { open: false, token: null, sending: false, greeted: false };

  // --------------------------------- Helpers UI ---------------------------------
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function scrollDown() { el.body.scrollTop = el.body.scrollHeight; }

  function addMessage(role, text, sources) {
    var msg = document.createElement("div");
    msg.className = "aria-msg " + role;
    var inner = "";
    if (role === "bot") inner += '<div class="av">' + ICON_BELL + "</div>";
    var srcHtml = "";
    if (sources && sources.length) {
      srcHtml = '<div class="aria-sources">' +
        sources.map(function (s) { return '<span class="aria-chip">' + esc(s) + "</span>"; }).join("") +
        "</div>";
    }
    inner += '<div class="aria-bubble">' + esc(text) + srcHtml + "</div>";
    msg.innerHTML = inner;
    el.body.appendChild(msg);
    scrollDown();
    return msg;
  }

  function showTyping() {
    var t = document.createElement("div");
    t.className = "aria-msg bot aria-typing";
    t.innerHTML = '<div class="av">' + ICON_BELL + '</div><div class="aria-bubble"><i></i><i></i><i></i></div>';
    el.body.appendChild(t);
    scrollDown();
    return t;
  }

  function addSuggestions() {
    var s = document.createElement("div");
    s.className = "aria-suggest";
    SUGGESTIONS.forEach(function (q) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = q;
      b.addEventListener("click", function () { s.remove(); submit(q); });
      s.appendChild(b);
    });
    el.body.appendChild(s);
    scrollDown();
  }

  // --------------------------------- Rete / API ---------------------------------
  function apiFetch(path, opts) {
    return fetch(cfg.apiUrl.replace(/\/$/, "") + path, opts);
  }

  function ensureSession() {
    if (state.token) return Promise.resolve(state.token);
    // token in sessionStorage (sopravvive alla navigazione, scade col TTL server)
    var cached = sessionRead();
    if (cached) { state.token = cached; return Promise.resolve(cached); }
    return apiFetch("/api/session", {
      method: "POST",
      headers: { "X-API-Key": cfg.apiKey },
    }).then(function (r) {
      if (!r.ok) throw new Error("session " + r.status);
      return r.json();
    }).then(function (data) {
      state.token = data.token;
      sessionWrite(data.token, data.expires_in);
      return data.token;
    });
  }

  function sendToApi(message) {
    return ensureSession().then(function (token) {
      return apiFetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
        body: JSON.stringify({ message: message }),
      });
    }).then(function (r) {
      if (r.status === 401) { // token scaduto: riprova una volta
        state.token = null; sessionClear();
        return ensureSession().then(function (token) {
          return apiFetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
            body: JSON.stringify({ message: message }),
          });
        });
      }
      return r;
    }).then(function (r) {
      if (r.status === 429) throw friendly("Troppe richieste in poco tempo. Riprova tra un momento.");
      if (!r.ok) throw friendly("Il servizio non è al momento disponibile. Riprova più tardi o contatta la reception.");
      return r.json();
    });
  }

  function friendly(msg) { var e = new Error(msg); e.friendly = true; return e; }

  // sessionStorage con scadenza
  var SKEY = "aria_token_" + (cfg.apiKey || "x");
  function sessionWrite(tok, ttl) {
    try { sessionStorage.setItem(SKEY, JSON.stringify({ t: tok, exp: Date.now() + (ttl || 300) * 1000 - 5000 })); } catch (e) {}
  }
  function sessionRead() {
    try { var v = JSON.parse(sessionStorage.getItem(SKEY) || "null"); return v && v.exp > Date.now() ? v.t : null; } catch (e) { return null; }
  }
  function sessionClear() { try { sessionStorage.removeItem(SKEY); } catch (e) {} }

  // --------------------------------- Modalità demo (senza backend) ---------------------------------
  function demoReply(message) {
    var q = message.toLowerCase();
    var kb = [
      { k: ["colazione", "breakfast"], t: "La colazione è servita a buffet dalle 7:00 alle 10:30 ed è inclusa nel soggiorno. Sono disponibili opzioni senza glutine e bevande vegetali.", s: ["Colazione a buffet"] },
      { k: ["check-in", "check in", "arrivo", "checkin"], t: "Il check-in è dalle 14:00, il check-out entro le 11:00. La reception è aperta 24 ore su 24 e offre deposito bagagli gratuito.", s: ["Reception e check-in"] },
      { k: ["parcheggio", "auto", "macchina", "posto auto"], t: "Sì: parcheggio privato coperto a 15 € a notte, con 2 colonnine di ricarica per auto elettriche. In alta stagione conviene prenotare il posto.", s: ["Parcheggio"] },
      { k: ["wifi", "wi-fi", "internet", "connessione"], t: "Il Wi-Fi in fibra è gratuito in tutte le camere e nelle aree comuni. In camera trovi rete e password sul cartoncino accanto al telefono.", s: ["Wi-Fi e connettività"] },
      { k: ["cane", "gatto", "animal", "pet"], t: "Gli animali fino a 20 kg sono benvenuti con un supplemento di 10 € a notte. Da segnalare in fase di prenotazione; non ammessi al ristorante e nell'area benessere.", s: ["Animali domestici"] },
      { k: ["spa", "piscina", "benessere", "palestra", "sauna"], t: "Il centro benessere ha piscina coperta riscaldata (8:00–20:00), sauna, bagno turco e palestra (6:00–22:00). La piscina è inclusa; i massaggi si prenotano in reception.", s: ["Spa, piscina e palestra"] },
      { k: ["ristorante", "cena", "pranzo", "mangiare"], t: "Il ristorante \"La Terrazza\" è al primo piano: pranzo 12:30–14:30, cena 19:30–22:30, con opzioni vegetariane, vegane e senza glutine. Prenotazione consigliata.", s: ["Ristorante La Terrazza"] },
      { k: ["prenot", "camera", "disponibil", "book"], t: "Con piacere! Posso raccogliere una richiesta di prenotazione: dimmi nome, email, date di check-in e check-out e numero di ospiti. La reception ti confermerà via email.", s: [] },
      { k: ["cancella", "disdet", "rimborso"], t: "La cancellazione è gratuita fino a 48 ore prima dell'arrivo; oltre, viene addebitata la prima notte. Le tariffe non rimborsabili non prevedono rimborso.", s: ["Politica di cancellazione"] },
    ];
    for (var i = 0; i < kb.length; i++) {
      for (var j = 0; j < kb[i].k.length; j++) {
        if (q.indexOf(kb[i].k[j]) !== -1) return { reply: kb[i].t, sources: kb[i].s };
      }
    }
    return {
      reply: "Non ho questa informazione con certezza, ma posso farla verificare alla reception. Vuoi che raccolga i tuoi contatti? (Questa è una demo con risposte simulate.)",
      sources: [],
    };
  }

  // --------------------------------- Invio messaggio ---------------------------------
  function submit(text) {
    text = (text || el.input.value).trim();
    if (!text || state.sending) return;
    var sug = el.body.querySelector(".aria-suggest"); if (sug) sug.remove();
    addMessage("user", text);
    el.input.value = ""; autoGrow(); updateSend();
    state.sending = true; updateSend();
    var typing = showTyping();

    var work = cfg.demo
      ? new Promise(function (res) { setTimeout(function () { res(demoReply(text)); }, 500 + Math.random() * 500); })
      : sendToApi(text);

    work.then(function (data) {
      typing.remove();
      addMessage("bot", data.reply, data.sources);
    }).catch(function (err) {
      typing.remove();
      var m = addMessage("bot", err && err.friendly ? err.message : "Ops, qualcosa è andato storto. Riprova o contatta la reception.");
      m.querySelector(".aria-bubble").classList.add("aria-err");
    }).then(function () {
      state.sending = false; updateSend(); el.input.focus();
    });
  }

  // --------------------------------- Apri / chiudi ---------------------------------
  function open() {
    state.open = true; wrap.classList.add("open");
    if (!state.greeted) {
      state.greeted = true;
      addMessage("bot", cfg.greeting);
      addSuggestions();
    }
    setTimeout(function () { el.input.focus(); }, 240);
  }
  function close() { state.open = false; wrap.classList.remove("open"); el.launcher.focus(); }

  // --------------------------------- Eventi ---------------------------------
  function autoGrow() { el.input.style.height = "auto"; el.input.style.height = Math.min(el.input.scrollHeight, 96) + "px"; }
  function updateSend() { el.send.disabled = state.sending || el.input.value.trim() === ""; }

  el.launcher.addEventListener("click", open);
  el.close.addEventListener("click", close);
  el.send.addEventListener("click", function () { submit(); });
  el.input.addEventListener("input", function () { autoGrow(); updateSend(); });
  el.input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && state.open) close(); });

  // API pubblica minima
  window.Aria = { open: open, close: close, config: cfg };
})();
