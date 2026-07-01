-- =============================================================================
-- 01_schema.sql
-- Schema del database AI Concierge: estensione pgvector, ruolo applicativo,
-- tre tabelle (rooms, knowledge_base, booking_requests) e Row-Level Security
-- per l'isolamento multi-tenant.
--
-- Eseguito automaticamente al PRIMO avvio del container Postgres
-- (cartella /docker-entrypoint-initdb.d). Gira come SUPERUSER.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Estensione pgvector (ricerca semantica / embedding)
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- NOTA sul ruolo applicativo:
-- Il ruolo NON-superuser 'app_user' viene creato dallo script precedente
-- (00_create_app_role.sh), perché la sua password arriva da una variabile
-- d'ambiente e gli script .sql non possono leggerle.
--
-- PERCHÉ SERVE un ruolo non-superuser: in PostgreSQL i SUPERUSER bypassano
-- SEMPRE la RLS. Se il backend si collegasse come 'postgres', l'isolamento
-- tra hotel NON sarebbe applicato. Il backend DEVE connettersi come 'app_user'.
-- ---------------------------------------------------------------------------

-- =============================================================================
-- TABELLA: rooms — dati strutturati e iper-specifici delle stanze
-- Approccio ibrido: colonne fisse + campi JSONB per i dettagli flessibili.
-- =============================================================================
CREATE TABLE rooms (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,                -- hotel proprietario (chiave RLS)
    room_number VARCHAR(10) NOT NULL,
    room_type VARCHAR(50) NOT NULL,
    floor INT NOT NULL,
    square_meters INT NOT NULL,
    max_guests INT NOT NULL,

    -- Focus Comfort Letto
    bed_type VARCHAR(50) NOT NULL,
    mattress_type VARCHAR(50),
    bed_comfort_notes TEXT,

    -- Dettagli iper-specifici e flessibili degli elettrodomestici
    air_conditioning JSONB,
    refrigerator JSONB,
    view_and_exposure JSONB,

    -- Servizi standard veloci
    amenities TEXT[],

    UNIQUE (tenant_id, room_number)         -- numero stanza unico per hotel
);

-- =============================================================================
-- TABELLA: knowledge_base — menù, orari, eventi, servizi, indicazioni...
-- È ciò che permette al chatbot di "rispondere a tutto" via ricerca semantica.
-- =============================================================================
CREATE TABLE knowledge_base (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,                -- hotel proprietario (chiave RLS)
    category VARCHAR(50) NOT NULL,          -- 'ristorante', 'eventi', 'servizi'...
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,                  -- testo descrittivo completo (la "scheda")
    metadata JSONB,                         -- dati extra opzionali (es. orari strutturati)
    embedding vector(1024),                 -- impronta numerica (bge-m3 / e5: 1024 dim)
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indice HNSW per ricerca semantica veloce (distanza coseno)
CREATE INDEX knowledge_base_embedding_idx
    ON knowledge_base USING hnsw (embedding vector_cosine_ops);

-- =============================================================================
-- TABELLA: booking_requests — richieste di prenotazione raccolte dal chatbot
-- =============================================================================
CREATE TABLE booking_requests (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,                -- hotel destinatario (chiave RLS)
    session_id TEXT NOT NULL,               -- conversazione di origine
    guest_name VARCHAR(120) NOT NULL,
    guest_email VARCHAR(160) NOT NULL,
    guest_phone VARCHAR(40),
    room_type VARCHAR(50),
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    num_guests INT NOT NULL,
    notes TEXT,
    status VARCHAR(20) DEFAULT 'pending',   -- pending | confirmed | rejected
    created_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- TABELLA: tenants — configurazione/identità degli hotel (API key, domini)
--
-- CASO SPECIALE: NON è sotto la Row-Level Security per-tenant. È la tabella di
-- LOOKUP che, data l'API key ricevuta dal widget, determina QUALE tenant siamo:
-- va quindi consultata PRIMA di conoscere il tenant (altrimenti chicken-and-egg).
-- L'API key è PUBBLICA (identifica, non protegge); le difese reali sono
-- allowlist domini + rate limiting + token di sessione a vita breve.
-- =============================================================================
CREATE TABLE tenants (
    tenant_id       TEXT PRIMARY KEY,        -- es. 'hotel_alpha'
    name            TEXT NOT NULL,           -- nome leggibile
    api_key         TEXT NOT NULL UNIQUE,    -- chiave pubblica del widget
    allowed_domains TEXT[] NOT NULL DEFAULT '{}',  -- domini autorizzati (Origin/Referer)
    active          BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX tenants_api_key_idx ON tenants (api_key);

-- =============================================================================
-- ROW-LEVEL SECURITY
--
-- Per ogni tabella:
--   ENABLE  -> attiva la RLS
--   FORCE   -> applica la RLS ANCHE al proprietario della tabella (non solo
--              ai ruoli normali). Senza FORCE, il ruolo owner vedrebbe tutto.
--
-- Policy: una riga è visibile/modificabile solo se il suo tenant_id coincide
-- con la variabile di sessione 'app.current_tenant', impostata dal backend
-- all'inizio di ogni transazione con:  SET LOCAL app.current_tenant = '<id>'
--
-- current_setting(..., true) -> il secondo argomento 'true' evita un errore
-- se la variabile non è impostata (ritorna NULL): in quel caso nessuna riga
-- combacia, quindi il default è "non vedo nulla" (fail-safe).
-- =============================================================================

-- rooms ----------------------------------------------------------------------
ALTER TABLE rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE rooms FORCE  ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON rooms
    USING (tenant_id = current_setting('app.current_tenant', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant', true));

-- knowledge_base -------------------------------------------------------------
ALTER TABLE knowledge_base ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_base FORCE  ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON knowledge_base
    USING (tenant_id = current_setting('app.current_tenant', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant', true));

-- booking_requests -----------------------------------------------------------
ALTER TABLE booking_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE booking_requests FORCE  ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON booking_requests
    USING (tenant_id = current_setting('app.current_tenant', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant', true));

-- =============================================================================
-- PRIVILEGI per il ruolo applicativo
-- Il ruolo app può leggere/scrivere i dati, ma NON è owner e NON è superuser,
-- quindi la RLS lo vincola sempre.
-- =============================================================================
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Default privileges: le GRANT qui sopra coprono solo le tabelle/sequenze che
-- esistono ORA. Questo blocco assicura che anche gli oggetti creati in FUTURO
-- (es. migrazioni al Passo 6) siano automaticamente accessibili ad app_user,
-- senza doversi ricordare di rifare la GRANT. Vale per gli oggetti creati dal
-- ruolo che esegue questo script (il superuser di init/migrazioni).
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO app_user;

-- La tabella 'tenants' è configurazione: il backend deve poterla LEGGERE (per
-- il lookup dell'API key) ma non modificarla. Least-privilege: revochiamo le
-- scritture ereditate dalla GRANT generica qui sopra. Il provisioning di un
-- nuovo hotel (INSERT/UPDATE su tenants) resta compito del superuser/admin.
REVOKE INSERT, UPDATE, DELETE ON tenants FROM app_user;
