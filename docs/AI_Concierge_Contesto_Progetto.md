# Contesto di Progetto: AI Concierge (SaaS)

**Data Ultimo Aggiornamento:** 11 Giugno 2026
**Stato:** Architettura definita — pronta per la fase di sviluppo

> **A cosa serve questo documento**
> È la base di conoscenza completa del progetto. Se viene fornito da solo in una chat nuova, deve bastare a capire esattamente cosa stiamo costruendo, come funziona e com'è strutturato, così da poter continuare a lavorare senza altre informazioni.
>
> **Come leggerlo:** ogni sezione tecnica ha un riquadro **"In parole semplici"** che spiega il concetto senza gergo. Chi non è tecnico può leggere solo quei riquadri e capire tutto il progetto.

---

## 1. Cos'è il prodotto

Un **assistente virtuale (chatbot)** che un'azienda integra nel proprio sito web. L'assistente conosce in modo approfondito quell'azienda e risponde agli utenti praticamente a **qualsiasi domanda** la riguardi, in linguaggio naturale.

Il **caso d'uso principale e d'esempio è l'hotel**, ma l'architettura è pensata per essere **generale**: lo stesso sistema può servire ristoranti, cliniche, palestre, agenzie e altre realtà, cambiando solo i dati caricati.

Per un hotel, il chatbot deve poter rispondere su tutto: dettagli iper-specifici delle stanze, menù e orari del ristorante, eventi, dove si trovano i bagni, orari della reception, politiche di cancellazione, servizi, posizione e indicazioni, e qualunque altro dettaglio raccolto. Inoltre svolge due funzioni attive:

1. **Verificare prezzi e disponibilità in tempo reale**, collegandosi al gestionale dell'hotel (PMS).
2. **Raccogliere una richiesta di prenotazione** dall'utente e inoltrarla alla reception, che la conferma via email.

> **In parole semplici**
> È un receptionist digitale sul sito, attivo 24 ore su 24, che sa rispondere a qualunque domanda sull'hotel e può anche raccogliere una richiesta di prenotazione da girare alla reception. L'hotel è l'esempio principale, ma lo stesso strumento si adatta ad altre attività.

**Modello di business:** vendita **diretta e su misura**. Ci si presenta alla singola azienda, si fa un sopralluogo, si raccolgono **tutti** i dati possibili e si configura il sistema caso per caso. Non è un prodotto "scatola chiusa" venduto in massa: ogni installazione è personalizzata.

---

## 2. Il vincolo che decide tutta l'architettura: Privacy & GDPR

Tutto il resto nasce da qui. **Non si usano intelligenze artificiali statunitensi (es. OpenAI).** Il "cervello" dell'IA gira interamente su **server europei controllati da noi**. I dati degli utenti vengono elaborati in memoria e **non vengono salvati né usati per addestrare modelli**.

> **In parole semplici**
> Molti chatbot mandano i dati degli utenti negli Stati Uniti. Noi no: teniamo tutto in Europa, su macchine nostre. Per un'azienda europea è un forte argomento di vendita, perché il GDPR la obbliga a proteggere i dati dei suoi clienti.

---

## 3. Lo stack tecnologico

| Componente | Tecnologia | A cosa serve |
|---|---|---|
| **Widget (sul sito cliente)** | Vanilla JavaScript (ES6+) + CSS isolato con **Shadow DOM** | La finestra di chat, iniettata nel sito e isolata dal suo stile |
| **Backend** | Python 3.11 + **FastAPI** (asincrono) | Il "centralino" che riceve le domande e coordina tutto |
| **Cervello IA** | **vLLM** (produzione) / **Ollama** (sviluppo), modello **Llama 3 8B Instruct** o **Mistral 7B** | Capisce le domande e scrive le risposte in linguaggio naturale |
| **Modello di Embedding** | Modello locale multilingue (es. **bge-m3** / **multilingual-e5**) | Trasforma testi e domande in "impronte numeriche" per la ricerca semantica |
| **Database** | **PostgreSQL** + estensione **pgvector** | Salva dati strutturati, knowledge base e impronte numeriche per la ricerca |
| **Memoria conversazioni** | **Redis** | Tiene a mente ogni chat in corso, isolata, con cancellazione automatica (TTL) |
| **Confezionamento** | **Docker & Docker Compose** | "Scatole" standard che fanno girare tutto allo stesso modo ovunque |
| **Sicurezza connessione (HTTPS)** | **Caddy Server** | Gestisce in automatico i certificati SSL/TLS (il lucchetto) via Let's Encrypt |
| **Invio email** | Servizio SMTP/email europeo | Invia la richiesta di prenotazione alla reception |
| **Hosting** | Server dedicato europeo con **GPU** | La macchina fisica che fa girare l'IA (vedi sez. 12) |

> **In parole semplici**
> Il **widget** è la chat che vede l'utente. Il **backend** è il cameriere che prende l'ordine. L'**IA** è lo chef che scrive la risposta. Il **database** è la dispensa con tutte le informazioni. **Docker** è il modo per spostare l'intera cucina ovunque senza rompere nulla.

---

## 4. Come funziona una richiesta, dall'inizio alla fine

Questo è il flusso di ogni messaggio che un utente scrive nella chat:

1. L'utente scrive una domanda nel **widget** sul sito dell'hotel.
2. Il widget invia la domanda al **backend**, allegando l'identità dell'hotel e un identificativo univoco della conversazione (`session_id`).
3. Il backend recupera dalla **memoria (Redis)** lo storico di *quella* conversazione.
4. Il backend cerca le informazioni utili: **ricerca semantica** nella knowledge base per le domande libere, e/o **function calling** per dati vivi (prezzi/disponibilità dal PMS) o azioni (prenotazione).
5. Backend invia all'**IA**: le regole di risposta + le informazioni trovate + lo storico chat.
6. L'**IA** scrive la risposta in linguaggio naturale, basandosi **solo** sui dati forniti.
7. La risposta torna al widget; lo storico aggiornato viene salvato in Redis.

> **In parole semplici**
> Ogni volta che qualcuno scrive, il sistema: capisce chi è (quale hotel, quale conversazione), recupera la cronologia di quella chat, va a cercare le informazioni giuste, le passa all'IA con le regole su come rispondere, e rimanda indietro la risposta. Tutto in un paio di secondi.

---

## 5. Sessioni e concorrenza: tante persone insieme, zero interferenze

Sul sito di uno stesso hotel — o di hotel diversi — possono esserci **molte persone che chattano contemporaneamente**. Il sistema deve garantire che nessuna conversazione si mescoli con un'altra e che nessun dato passi da una struttura all'altra.

Come viene garantito:

- **Backend stateless.** Il backend non "ricorda" nulla tra una richiesta e l'altra: ogni messaggio porta con sé tutto ciò che serve (identità hotel + `session_id`). Questo permette di gestire tante richieste in parallelo senza confusione.
- **Sessioni isolate in Redis.** Ogni conversazione è salvata con una chiave univoca del tipo `tenant_id:session_id`. Due utenti diversi = due chiavi diverse = due memorie completamente separate. Impossibile che si sovrappongano.
- **Isolamento tra hotel garantito dal database** (vedi sez. 6): anche con molte richieste simultanee, un hotel non può mai leggere i dati di un altro.
- **Concorrenza efficiente sull'IA.** vLLM usa il *continuous batching*: elabora molte conversazioni in parallelo sulla stessa GPU in modo efficiente. Gli hotel medio-piccoli generano traffico basso e a raffiche, quindi una sola buona GPU regge molti utenti e molti hotel insieme.

> **In parole semplici**
> Ogni conversazione ha un'etichetta unica, come un numero di tavolo al ristorante: il cameriere non porta mai il piatto al tavolo sbagliato, nemmeno quando il locale è pieno. E le cucine dei vari hotel sono separate per legge interna del database: nessuno può sbirciare nella dispensa di un altro.

---

## 6. Multi-Tenancy: come teniamo separati gli hotel

"Multi-tenancy" significa: **un solo sistema serve tanti hotel diversi**, ma ognuno vede **solo** i propri dati. Tutti gli hotel condividono lo stesso software e lo stesso database, per ottimizzare RAM e CPU.

### Soluzione: Row-Level Security (RLS) + `tenant_id`

Ogni riga di ogni tabella è etichettata con l'hotel a cui appartiene (`tenant_id`). Si attiva la **Row-Level Security** nativa di PostgreSQL: il database stesso, a livello di motore, **rifiuta automaticamente** qualsiasi riga che non appartenga all'hotel della richiesta corrente. Non dipende dalla correttezza del codice applicativo: lo garantisce il database.

L'identità dell'hotel viene impostata **dentro la singola transazione** con `SET LOCAL`. È un dettaglio cruciale: così l'identità è valida solo per quella transazione e non può "rimanere attaccata" a una connessione riutilizzata (le app ad alto traffico riusano le connessioni: senza `SET LOCAL`, un hotel potrebbe ereditare il contesto di un altro — fuga di dati).

```sql
-- Ogni tabella ha la colonna che indica l'hotel proprietario
ALTER TABLE rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE rooms FORCE ROW LEVEL SECURITY;

-- Regola: vedi solo le righe del tuo hotel
CREATE POLICY tenant_isolation ON rooms
  USING (tenant_id = current_setting('app.current_tenant', true));
```

```python
# Nel backend, all'inizio di OGNI transazione (scoped, non persiste sulla connessione):
await conn.execute("SET LOCAL app.current_tenant = $1", tenant_id)
```

> **In parole semplici**
> Immagina un palazzo con tanti appartamenti (gli hotel) e un solo portiere (il nostro sistema). Dobbiamo essere certi che il portiere non consegni mai la posta dell'appartamento A all'appartamento B. La regola di sicurezza del database fa proprio da serratura automatica: prima di ogni operazione il sistema dichiara "sto servendo l'hotel X" e il database mostra solo le cose dell'hotel X.
>
> Se un cliente molto sensibile lo richiede, gli si può comunque assegnare un **database tutto suo, separato fisicamente**.

---

## 7. Sicurezza del widget e della API Key

Ogni hotel ha una **API Key** univoca che il widget invia nell'header per identificarsi. Attenzione: il widget gira nel browser dell'utente, quindi **chiunque apra gli strumenti del browser può leggere quella chiave**. La API Key serve a **identificare** l'hotel, non a proteggerlo: è di fatto pubblica. Per questo servono difese vere:

1. **Allowlist dei domini (controllo Origin/Referer).** Ogni hotel ha registrati i propri domini autorizzati. Il backend accetta richieste solo se arrivano davvero dal sito di quell'hotel. Una chiave copiata e usata da un altro sito viene rifiutata.
2. **Rate limiting.** Numero massimo di richieste al minuto per chiave/IP. Blocca lo scraping del database e l'abuso della GPU (la voce di costo più cara).
3. **Token di sessione a vita breve (consigliato).** Quando il widget si carica da un dominio autorizzato, il backend emette un token temporaneo (es. JWT) valido pochi minuti, legato al `session_id`. È quel token, non la chiave, a viaggiare nelle richieste successive. Anche se intercettato, scade subito.

> **In parole semplici**
> La chiave è un "cartellino col nome", non una password: chiunque può leggerla. Quindi aggiungiamo un **buttafuori** che controlla che tu venga davvero dal sito dell'hotel giusto, un **limite** al numero di domande, e un **pass temporaneo** che scade dopo pochi minuti.

---

## 8. Il cuore del sistema: come l'IA risponde "a qualsiasi cosa"

Questo è il punto più delicato dell'architettura. Durante il sopralluogo si raccolgono **tutti** i dati possibili dell'hotel (menù, orari ristorante, eventi, dove sono i bagni, servizi, policy, indicazioni…). Il problema: questi dati sono in gran parte **testo descrittivo e imprevedibile**. Non si possono incolonnare tutti in una tabella SQL rigida, e non si può nemmeno dare tutto in pasto all'IA a ogni domanda (sarebbe troppo lungo, lento e costoso).

La soluzione è gestire l'informazione in **tre modi diversi a seconda del tipo**, e dare all'IA solo i pezzi rilevanti per ogni domanda.

### A) Knowledge base + ricerca semantica → per le domande libere

Tutte le informazioni descrittive (menù, orari, eventi, "dove sono i bagni", servizi, regole, indicazioni…) vengono salvate come **schede di conoscenza** nella tabella `knowledge_base`. Ogni scheda viene trasformata in un'**"impronta numerica" (embedding)** con un modello locale e salvata in PostgreSQL tramite **pgvector**.

Quando l'utente fa una domanda, il backend trasforma anche **la domanda** in un'impronta numerica e chiede al database: *"quali schede assomigliano di più a questa domanda?"*. Recupera le 3-5 più pertinenti e le passa all'IA, che formula la risposta. Questa tecnica si chiama **RAG (Retrieval-Augmented Generation)**.

> **In parole semplici**
> Invece di costringere l'IA a imparare a memoria un manuale enorme, gli diamo una biblioteca ben organizzata. A ogni domanda, il sistema pesca al volo solo le 2-3 pagine giuste e le mette davanti all'IA, che legge e risponde. Così può rispondere praticamente a tutto, anche a cose che non avevamo previsto come "campo" del database, semplicemente perché l'informazione è scritta in una scheda.

### B) Dati strutturati delle stanze → per i dettagli iper-precisi

Per i dettagli tecnici e precisi delle camere (gradi del condizionatore, litri del frigo, tipo di materasso) si usa una tabella strutturata `rooms` con campi fissi + campi flessibili **JSONB** (vedi sez. 9). Quando serve un dato preciso su una stanza, il backend lo legge direttamente e lo passa all'IA. La precisione qui conta più della libertà.

### C) Function calling → per i dati vivi e le azioni

Per ciò che cambia in tempo reale o richiede un'azione, l'IA **chiama uno strumento**:
- **Prezzi e disponibilità** → interroga il PMS (sez. 11).
- **Richiesta di prenotazione** → crea la richiesta e avvisa la reception (sez. 10).

> **In parole semplici**
> Tre cassetti diversi: la **biblioteca** (ricerca semantica) per le domande generiche, la **scheda tecnica** delle stanze per i numeri precisi, e il **telefono** (function calling) per chiedere prezzi al gestionale o inviare una prenotazione. Il sistema apre il cassetto giusto a seconda della domanda.

---

## 9. Design del Database

Tre gruppi di tabelle, tutte con `tenant_id` e protette da RLS (sez. 6).

### 9.1 `rooms` — dati strutturati e iper-specifici delle stanze

Approccio **ibrido Relazionale + JSONB**: colonne fisse per i dati standard, campi JSONB per i dettagli flessibili e imprevedibili degli elettrodomestici.

```sql
CREATE TABLE rooms (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,               -- hotel proprietario (RLS)
    room_number VARCHAR(10) NOT NULL,
    room_type VARCHAR(50) NOT NULL,
    floor INT NOT NULL,
    square_meters INT NOT NULL,
    max_guests INT NOT NULL,

    -- Focus Comfort Letto
    bed_type VARCHAR(50) NOT NULL,         -- es. 'Matrimoniale King Size'
    mattress_type VARCHAR(50),             -- es. 'Memory Foam ortopedico'
    bed_comfort_notes TEXT,                -- Note testuali per l'IA

    -- Campi JSONB per dettagli iper-specifici e flessibili
    air_conditioning JSONB,
    refrigerator JSONB,
    view_and_exposure JSONB,

    -- Servizi standard veloci
    amenities TEXT[],                      -- es. ['Wi-Fi Gratuito', 'Cassaforte']

    UNIQUE (tenant_id, room_number)        -- numero stanza unico per hotel
);
```

Esempio di campo JSONB — `air_conditioning`:

```json
{
  "disponibile": true,
  "modello": "Daikin Silent 2026",
  "controllo_remoto": "Tramite domotica a schermo o telecomando",
  "range_temperatura": {
    "min_celsius": 16,
    "max_celsius": 30,
    "supporta_kelvin": true,
    "nota_tecnica": "Il termostato mostra sia °C che K. La conversione la calcola il backend, non l'IA."
  },
  "silenzioso": "Sì, modalità notturna a 19 dB"
}
```

Esempio di campo JSONB — `refrigerator`:

```json
{
  "disponibile": true,
  "tipo": "Minibar a incasso maggiorato",
  "capacita_litri": 45,
  "ha_congelatore": true,
  "dettagli_congelatore": {
    "presente": true,
    "dimensione": "Piccolo scomparto superiore da 5 litri",
    "temperatura_minima": -6,
    "capacita_ghiaccio": "Fino a 2 vaschette per cubetti di ghiaccio"
  },
  "incluso_nel_prezzo": "Bevande di benvenuto incluse, rifornimenti a pagamento"
}
```

> **Consiglio:** definire un **JSON Schema** per ogni campo JSONB e validarlo in scrittura, così l'IA riceve sempre dati nella stessa struttura.

### 9.2 `knowledge_base` — tutto il resto (menù, orari, eventi, servizi, indicazioni…)

Qui finisce qualsiasi informazione descrittiva raccolta nel sopralluogo. È ciò che permette al chatbot di "rispondere a tutto".

```sql
CREATE EXTENSION IF NOT EXISTS vector;   -- pgvector

CREATE TABLE knowledge_base (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,               -- hotel proprietario (RLS)
    category VARCHAR(50) NOT NULL,         -- es. 'ristorante', 'eventi', 'servizi', 'strutture', 'policy'
    title VARCHAR(200) NOT NULL,           -- es. 'Orari del ristorante'
    content TEXT NOT NULL,                 -- il testo descrittivo completo (la "scheda")
    metadata JSONB,                        -- dati extra opzionali (es. orari in forma strutturata)
    embedding vector(1024),                -- impronta numerica per la ricerca semantica
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indice per ricerca semantica veloce
CREATE INDEX ON knowledge_base USING hnsw (embedding vector_cosine_ops);
```

Esempio di scheda:

```text
category: 'ristorante'
title:    'Orari e prenotazioni del ristorante'
content:  'Il ristorante interno "La Terrazza" è al primo piano. Colazione 7:00–10:30
           (a buffet, inclusa nel soggiorno). Pranzo 12:30–14:30. Cena 19:30–22:30.
           Prenotazione consigliata alla reception o al numero interno 102. Menù alla
           carta con opzioni vegetariane, vegane e senza glutine. I bagni per gli ospiti
           del ristorante sono accanto all'ingresso, sulla destra.'
```

> Numeri esatti che devono essere sempre precisi (es. orari) si possono mettere **anche** in `metadata` in forma strutturata, così il backend può fornirli all'IA senza rischio di errore.

### 9.3 `booking_requests` — le richieste di prenotazione (sez. 10)

```sql
CREATE TABLE booking_requests (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,               -- hotel destinatario (RLS)
    session_id TEXT NOT NULL,              -- conversazione di origine
    guest_name VARCHAR(120) NOT NULL,
    guest_email VARCHAR(160) NOT NULL,
    guest_phone VARCHAR(40),
    room_type VARCHAR(50),
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    num_guests INT NOT NULL,
    notes TEXT,                            -- richieste particolari dell'utente
    status VARCHAR(20) DEFAULT 'pending',  -- pending | confirmed | rejected
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 10. Funzione di prenotazione via chatbot

Il chatbot può **raccogliere una richiesta di prenotazione** e inoltrarla alla reception. **Non è una conferma automatica**: è una richiesta che la reception conferma manualmente via email. Va comunicato chiaramente all'utente per non creare false aspettative.

### Flusso

1. L'utente esprime l'intenzione di prenotare. L'IA, tramite **function calling**, raccoglie nella conversazione i dati necessari: nome, email, (telefono), tipo stanza, date check-in/check-out, numero ospiti, note.
2. Se possibile, il backend verifica la disponibilità sul PMS (sez. 11) prima di procedere.
3. Il backend salva la richiesta in `booking_requests` con stato `pending` e invia un'**email alla reception** con tutti i dettagli.
4. Il chatbot conferma all'utente che la **richiesta** è stata inviata e che riceverà conferma via email all'indirizzo fornito.
5. La reception valuta e conferma (o rifiuta) **rispondendo via email direttamente all'utente**; aggiorna lo stato della richiesta.

> **In parole semplici**
> L'utente può dire "vorrei prenotare una doppia per sabato": il chatbot raccoglie i dati come farebbe un receptionist al telefono, controlla se c'è posto, e manda la richiesta via email alla reception. La reception poi conferma scrivendo all'utente. Il chatbot non "vende" la stanza da solo: la prepara e la passa a una persona.

> **Nota privacy:** la richiesta contiene dati personali dell'utente (nome, email). Vanno gestiti secondo GDPR: consenso nel widget, conservazione limitata nel tempo, accesso ristretto.

---

## 11. Strategia PMS: integrazione su misura, caso per caso

Il gestionale (PMS) è la parte più variabile del progetto: ogni hotel ne ha uno diverso, alcuni moderni, alcuni vecchissimi, alcuni senza alcuna possibilità di collegamento automatico. Coerentemente con la vendita diretta, **l'integrazione PMS si fa su misura per ogni cliente**, durante il sopralluogo iniziale.

### Schema decisionale per il collegamento al PMS

| Situazione del PMS | Soluzione di integrazione |
|---|---|
| **Ha API moderne (REST/JSON)** | Collegamento diretto in tempo reale tramite un *adapter* dedicato. Caso ideale. |
| **Niente API, ma c'è un Channel Manager** | Ci si collega al channel manager per leggere disponibilità e tariffe. |
| **Solo export/file** (CSV, Excel, iCal) | Sincronizzazione periodica programmata: il sistema rilegge i dati ogni X minuti. |
| **Nessuna automazione possibile** | Calendario gestito a mano dall'hotel nel nostro pannello, oppure il chatbot raccoglie il contatto e risponde "verifichiamo e la ricontattiamo". |

### Nota tecnica

Anche se l'integrazione è su misura, si definisce **un'interfaccia comune** (adapter pattern): il resto del sistema parla sempre lo stesso "linguaggio" (`get_disponibilita()`, `get_prezzo()`), mentre dietro ogni hotel ha il suo connettore specifico. Così il lavoro su misura resta isolato e non tocca il cuore del sistema. Le risposte del PMS vanno messe in **cache breve su Redis**, perché le interrogazioni live possono essere lente o limitate dal gestionale.

> **In parole semplici**
> Non esiste un collegamento universale per tutti i gestionali. Per ogni hotel guardiamo cosa ha e scegliamo la strada migliore, dal collegamento automatico perfetto fino — nei casi peggiori — a un calendario aggiornato a mano. L'importante è che il chatbot non dia mai un prezzo o una disponibilità sbagliata.

---

## 12. Governance delle risposte: evitare che l'IA "divaghi"

I modelli locali medio-piccoli (7-8B) tendono a **inventare**, soprattutto su numeri e dettagli precisi, se lasciati liberi. Tre regole per tenerli sotto controllo:

1. **Regole sempre presenti (system prompt).** Le istruzioni su come rispondere stanno nel *system prompt*, che **viene riletto automaticamente a ogni risposta** (è sempre in testa al contesto). Vanno scritte chiare e con esempi.
2. **Ancoraggio ai dati (la leva più importante).** All'IA si danno **solo** i dati pertinenti alla domanda (le schede recuperate, i dati della stanza), con istruzione esplicita: *"rispondi SOLO con questi dati; se l'informazione non c'è, dillo e proponi di far verificare alla reception"*. Niente invenzioni.
3. **Dati critici calcolati dal backend, non generati.** Prezzi, orari, politiche e **conversioni** (es. Celsius→Kelvin) li fornisce il backend già pronti; l'IA li riporta soltanto. Non si lascia generare l'IA su numeri che devono essere esatti.

**Da evitare:** preimpostare *tutte* le risposte. Si perderebbe il valore del chatbot (conversazione naturale, capacità di capire domande formulate in mille modi) e diventerebbe ingestibile. L'approccio corretto è **ibrido**: dati e numeri **deterministici** dal backend, **frasi naturali** generate dall'IA attorno a quei dati.

> **In parole semplici**
> L'IA è bravissima a *parlare bene*, ma non ci si può fidare quando deve *ricordare numeri precisi*. Quindi: i numeri glieli diamo noi già pronti e le diciamo "non inventare nulla fuori da questi dati"; lei li trasforma in una bella frase. Le regole di comportamento sono sempre davanti ai suoi occhi a ogni risposta.

---

## 13. Infrastruttura: server dedicato europeo con GPU

Per un progetto a lungo termine con più hotel, l'IA self-hosted su un **server dedicato con GPU** è la scelta giusta:

- **Niente costi a consumo (token).** Si paga la macchina, non ogni singola risposta. Più hotel/conversazioni si servono, più il costo per risposta crolla.
- **Controllo totale su dati e modello.** Si allinea con l'argomento di vendita GDPR: i dati non escono mai dalla macchina europea.
- **Un modello, tanti hotel.** Lo stesso modello 8B serve tutti gli hotel insieme; il traffico degli hotel medio-piccoli è basso e a raffiche, quindi una sola buona GPU regge molti clienti.

**Decisioni pratiche:**

- **GPU.** Un modello 8B richiede ~16-24 GB di VRAM. Una **Nvidia L4 (24 GB)** o **A10G** è adeguata per partire e servire diversi hotel insieme (più il piccolo modello di embedding, che pesa poco).
- **Comprare vs noleggiare il server (~3.000 €).** *Comprare* dà controllo massimo ma richiede di ospitare la macchina in un datacenter europeo affidabile (uptime, raffreddamento, connettività). *Noleggiare* un server GPU dedicato (Hetzner, OVHcloud) ~200-500 €/mese dà lo stesso controllo software e la stessa conformità senza gestire l'hardware, ed è scalabile in minuti. **Consiglio: iniziare noleggiando**, e valutare l'acquisto quando il numero di hotel paganti lo giustifica (break-even dei 3.000 € intorno agli 8-12 mesi).
- **Punto debole da gestire: un solo server = un solo punto di rottura.** Prevedere backup dei dati e un piano di ripristino rapido; con molti hotel, un secondo server di riserva.

> **In parole semplici**
> Pagare l'IA "a risposta" conviene quando se ne usa poca; servendo tanti hotel ogni giorno conviene avere la propria macchina a costo fisso: più la usi, meno costa ogni risposta, e i dati restano a casa tua. Si parte affittando una macchina potente (niente grane di hardware) e se ne compra una propria solo quando i numeri lo ripagano. Unica accortezza: con una sola macchina, se si rompe sei fermo — quindi backup e piano B.

---

## 14. Prossimi Passi per lo Sviluppo

1. Avviare l'ambiente locale (PostgreSQL + pgvector + Redis) con Docker Compose.
2. Attivare RLS sulle tabelle e testare l'isolamento tra due hotel fittizi e tra sessioni simultanee.
3. Popolare i dati di test: 30 stanze fittizie (con JSONB) + una knowledge base d'esempio (menù, orari, eventi, servizi).
4. Implementare la pipeline di embedding (modello locale) e la ricerca semantica con pgvector.
5. Implementare la sicurezza del widget: allowlist domini + rate limiting + token di sessione.
6. Scrivere gli endpoint FastAPI: chat, gestione sessioni Redis, RAG sulla knowledge base, lettura stanze.
7. Definire il system prompt con le regole di risposta + i dati/calcoli deterministici (prezzi, orari, conversioni).
8. Implementare il function calling: richiesta di prenotazione (con email alla reception) e adapter PMS del primo hotel reale.
9. Scegliere e configurare il server GPU dedicato europeo (noleggio iniziale) con vLLM.

---

## Appendice — Glossario rapido

- **SaaS:** software venduto come servizio in abbonamento, ospitato da noi.
- **PMS:** *Property Management System*, il gestionale dell'hotel (prenotazioni, tariffe, disponibilità).
- **Multi-tenancy:** un solo sistema che serve tanti clienti tenendo i dati separati.
- **Tenant:** un singolo cliente/hotel all'interno del sistema condiviso.
- **RLS (Row-Level Security):** funzione di PostgreSQL che filtra le righe in automatico per tenant.
- **JSONB:** tipo di campo PostgreSQL per salvare dati flessibili e annidati.
- **Embedding:** "impronta numerica" di un testo, che permette di confrontare significati.
- **pgvector:** estensione di PostgreSQL per salvare e cercare embedding.
- **RAG (Retrieval-Augmented Generation):** recuperare i dati giusti e darli all'IA perché risponda basandosi su quelli.
- **Function calling:** l'IA che chiama uno "strumento" (es. interrogare il PMS, creare una prenotazione).
- **Grounding:** vincolare l'IA a rispondere solo dai dati forniti, senza inventare.
- **vLLM:** software che fa girare il modello IA in modo efficiente, anche con molte conversazioni in parallelo.
- **Shadow DOM:** tecnica che isola lo stile del widget dal resto del sito.
- **Token (LLM):** unità di testo elaborata dall'IA; con l'IA a consumo si paga a token.
