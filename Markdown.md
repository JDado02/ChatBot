# Contesto di Progetto: AI Hotel Concierge (SaaS)
**Data Ultimo Aggiornamento:** 9 Giugno 2026  
**Stato:** Fase di Progettazione Iniziale / Architettura Approvata

Questo documento serve come memoria storica e base di conoscenza per le sessioni di sviluppo future. Descrive l'architettura, lo stack tecnologico e le specifiche del database concordate per il progetto "AI Hotel Concierge".

---

## 1. Visione del Progetto & Requisiti
Il sistema è un software B2B in modalità **SaaS** rivolto a hotel (target iniziale: strutture di medie dimensioni, ~30 stanze). Consiste in un assistente virtuale (chatbot) integrabile nei siti web esistenti dei clienti per svolgere due compiti:
1. **Risposte Statiche:** Fornire dettagli fisici e di comfort iper-specifici sulle stanze attingendo dal database locale.
2. **Risposte Dinamiche:** Verificare prezzi e disponibilità in tempo reale interfacciandosi alle API del software gestionale dell'hotel (PMS).

### Vincolo Mandatario: Privacy & GDPR (On-Premise Cloud)
Per garantire la totale riservatezza dei dati e la conformità al GDPR, **non si utilizzano API esterne statunitensi (es. OpenAI)**. Il motore di calcolo dell'IA risiede interamente su un'infrastruttura Cloud Privata ed Europea controllata dal provider. I dati sensibili vengono elaborati in RAM e non vengono memorizzati o usati per il riaddestramento.

---

## 2. Stack Tecnologico Approvato

* **Frontend (Client-Side):** Vanilla JavaScript (ES6+) puro + CSS isolato tramite **Shadow DOM**. Viene distribuito come script statico indipendente, iniettato nel sito ospite. Comunica via HTTP Fetch API / WebSockets. Non usa Docker sul client.
* **Backend Framework:** Python 3.11 + **FastAPI** (Asincrono, performante, documentazione Swagger nativa).
* **AI Engine & Orchestration:** **vLLM** (Produzione) / **Ollama** (Sviluppo) per far girare localmente il modello Open-Source **Llama 3 (8B Instruct)** o **Mistral (7B)**. Supporto nativo al *Function Calling*.
* **Database Statico (Stanze):** **PostgreSQL** (singolo container Docker, isolamento multi-tenant).
* **Database Cache (Sessioni):** **Redis** per la gestione in RAM della cronologia dei messaggi e del contesto della chat.
* **Infrastruttura e DevOps:** **Docker & Docker Compose** per containerizzare l'ambiente server (FastAPI, Postgres, Redis, vLLM).
* **Reverse Proxy & HTTPS:** **Caddy Server** (inserito in Docker, gestisce in automatico l'emissione e il rinnovo dei certificati SSL/TLS tramite Let's Encrypt con un *Caddyfile* minimale).
* **Cloud Hosting:** Cloud Provider Europei (Hetzner, OVHcloud, Scaleway) su istanze dotate di GPU dedicate (es. Nvidia L4 / A10G).

---

## 3. Strategia Multi-Tenancy (Gestione multi-hotel)
È stata scelta la soluzione **Multi-Tenancy con Isolamento Logico a livello di Schema PostgreSQL**.
* Gira un unico container Docker di PostgreSQL per ottimizzare RAM e CPU.
* Ogni hotel ha il proprio **Schema dedicato** nel database (es. `hotel_splendid.rooms`, `hotel_royal.rooms`).
* Il widget invia una `API_KEY` univoca nell'header. FastAPI la valida e, prima di ogni query, imposta il percorso d'azione tramite `SET search_path TO hotel_id;`. Questo azzera il rischio di leak di dati tra strutture diverse.

---

## 4. Design del Database (Dettagli Iper-Specifici)
Per permettere all'IA di rispondere a domande estremamente granulari (gradi del condizionatore, presenza del freezer, comodità del letto) senza irrigidire la tabella SQL, si adotta un approccio **ibrido Relazionale + JSONB**.

### Schema SQL della Tabella `rooms` (Interna ad ogni Schema Hotel)
```sql
CREATE TABLE rooms (
    id SERIAL PRIMARY KEY,
    room_number VARCHAR(10) NOT NULL UNIQUE,
    room_type VARCHAR(50) NOT NULL,
    floor INT NOT NULL,
    square_meters INT NOT NULL,
    max_guests INT NOT NULL,
    
    -- Focus Comfort Letto
    bed_type VARCHAR(50) NOT NULL,        -- es. 'Matrimoniale King Size'
    mattress_type VARCHAR(50),            -- es. 'Memory Foam ortopedico'
    bed_comfort_notes TEXT,               -- Note testuali per l'IA sulla comodità

    -- Campi JSONB per flessibilità iper-specifica degli elettrodomestici
    air_conditioning JSONB,
    refrigerator JSONB,
    view_and_exposure JSONB,
    
    -- Array di stringhe per servizi standard veloci
    amenities TEXT[]                      -- es. ['Wi-Fi Gratuito', 'Cassaforte']
);
```
Esempio di Record JSONB inserito per il "Function Calling"
Quando l'utente interroga la chat, FastAPI estrae questi oggetti JSONB e li passa in pasto all'LLM locale, che formula la risposta in linguaggio naturale.

air_conditioning (Aria Condizionata)
```JSON
{
"disponibile": true,
"modello": "Daikin Silent 2026",
"controllo_remoto": "Tramite domotica a schermo o telecomando",
"range_temperatura": {
"min_celsius": 16,
"max_celsius": 30,
"supporta_kelvin": true,
"nota_tecnica": "Il termostato permette la visualizzazione sia in gradi Celsius (°C) che in Kelvin (K). 20°C corrispondono a 293.15 K."
},
"silenzioso": "Sì, modalità notturna a 19 dB"
}
refrigerator (Minibar / Frigorifero)
JSON
{
"disponibile": true,
"tipo": "Minibar a incasso maggiorato",
"capacita_litri": 45,
"ha_congelatore": true,
"dettagli_congelatore": {
"presente": true,
"dimensione": "Piccolo scomparto superiore da 5 litri",
"temperatura_minima": -6,
"capacita_ghiaccio": "Contiene fino a 2 vaschette per cubetti di ghiaccio"
},
"incluso_nel_prezzo": "Bevande di benvenuto incluse, rifornimenti a pagamento"
}
```
---

## 5. Prossimi Passi per lo Sviluppo
   Configurare l'ambiente di sviluppo locale avviando postgres e redis tramite Docker Compose.

Popolare lo schema di test con 30 stanze fittizie ricche di dati JSONB.

Scrivere gli endpoint FastAPI in Python e iniziare il Function Calling con Ollama.
