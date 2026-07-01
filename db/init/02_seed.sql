-- =============================================================================
-- 02_seed.sql
-- Dati di test per due hotel fittizi: 'hotel_alpha' (ricco) e 'hotel_beta'
-- (piccolo, per il contrasto multi-tenant). Servono a:
--   1) verificare l'isolamento RLS (vedi db/test/);
--   2) avere dati realistici per la pipeline di embedding + ricerca semantica.
--
-- Eseguito come SUPERUSER durante l'init: il superuser bypassa la RLS, quindi
-- può inserire righe per entrambi i tenant. Il backend, invece, userà
-- 'app_user' e vedrà solo il proprio tenant.
--
-- NOTA: il campo 'embedding' è lasciato NULL. Gli embedding reali vengono
-- generati dal modello locale nella pipeline applicativa (Passo 4).
-- =============================================================================

-- =============================================================================
-- HOTEL ALPHA — 30 stanze
-- Generate come 6 archetipi × 5 piani = 30 camere. Il numero stanza è
-- piano*100 + posizione (101..106, 201..206, ... 501..506). La vista cambia
-- con il piano (piani alti = vista mare) per dare varietà realistica ai dati.
-- =============================================================================
WITH archetipi (pos, room_type, sqm, max_guests, bed_type, mattress, bed_notes, ac, fridge, amenities) AS (
  VALUES
    (1, 'Singola Comfort', 18, 1, 'Singola',
     'Lattice ergonomico', 'Materasso singolo ortopedico, cuscino in memory.',
     '{"disponibile": true, "modello": "Mitsubishi Eco", "silenzioso": "Sì, 21 dB in modalità notte", "range_temperatura": {"min_celsius": 17, "max_celsius": 28}}'::jsonb,
     '{"disponibile": false}'::jsonb,
     ARRAY['Wi-Fi Gratuito', 'Scrivania', 'Cassaforte']),

    (2, 'Doppia Standard', 24, 2, 'Matrimoniale',
     'Memory Foam', 'Letto matrimoniale standard, due cuscini in memory.',
     '{"disponibile": true, "modello": "Daikin Comfort", "range_temperatura": {"min_celsius": 16, "max_celsius": 30}}'::jsonb,
     '{"disponibile": true, "tipo": "Minibar", "capacita_litri": 30, "ha_congelatore": false}'::jsonb,
     ARRAY['Wi-Fi Gratuito', 'Cassaforte', 'TV Smart']),

    (3, 'Doppia Deluxe', 28, 2, 'Matrimoniale King Size',
     'Memory Foam ortopedico', 'Letto regolabile, due cuscini in piuma e due in memory.',
     '{"disponibile": true, "modello": "Daikin Silent 2026", "silenzioso": "Sì, modalità notturna a 19 dB", "range_temperatura": {"min_celsius": 16, "max_celsius": 30, "supporta_kelvin": true}}'::jsonb,
     '{"disponibile": true, "tipo": "Minibar a incasso", "capacita_litri": 45, "ha_congelatore": true, "dettagli_congelatore": {"presente": true, "temperatura_minima": -6}}'::jsonb,
     ARRAY['Wi-Fi Gratuito', 'Cassaforte', 'TV Smart', 'Macchina caffè']),

    (4, 'Tripla Familiare', 32, 3, 'Matrimoniale + Singolo',
     'Pocket Spring', 'Matrimoniale più letto singolo, ideale per famiglie.',
     '{"disponibile": true, "modello": "Samsung WindFree", "range_temperatura": {"min_celsius": 16, "max_celsius": 30}}'::jsonb,
     '{"disponibile": true, "tipo": "Minibar", "capacita_litri": 40, "ha_congelatore": true}'::jsonb,
     ARRAY['Wi-Fi Gratuito', 'Cassaforte', 'TV Smart', 'Culla su richiesta']),

    (5, 'Suite Junior', 38, 3, 'Matrimoniale King Size',
     'Memory Foam premium', 'Zona notte separata, testiera imbottita.',
     '{"disponibile": true, "modello": "Daikin Silent 2026", "silenzioso": "Sì, 19 dB", "range_temperatura": {"min_celsius": 16, "max_celsius": 30, "supporta_kelvin": true}}'::jsonb,
     '{"disponibile": true, "tipo": "Minibar maggiorato", "capacita_litri": 55, "ha_congelatore": true, "incluso_nel_prezzo": "Bevande di benvenuto incluse"}'::jsonb,
     ARRAY['Wi-Fi Gratuito', 'Cassaforte', 'TV Smart', 'Macchina caffè', 'Accappatoio']),

    (6, 'Suite Panoramica', 48, 4, 'Matrimoniale + Divano letto',
     'Pocket Spring premium', 'Suite ampia con zona living separata e divano letto.',
     '{"disponibile": true, "modello": "Daikin Silent 2026", "silenzioso": "Sì, 18 dB", "range_temperatura": {"min_celsius": 16, "max_celsius": 30, "supporta_kelvin": true}}'::jsonb,
     '{"disponibile": true, "tipo": "Frigo maggiorato", "capacita_litri": 60, "ha_congelatore": true, "dettagli_congelatore": {"presente": true, "temperatura_minima": -8, "capacita_ghiaccio": "Fino a 2 vaschette"}}'::jsonb,
     ARRAY['Wi-Fi Gratuito', 'Cassaforte', 'TV Smart', 'Macchina caffè', 'Accappatoio', 'Jacuzzi'])
),
piani AS (SELECT generate_series(1, 5) AS fl)
INSERT INTO rooms
  (tenant_id, room_number, room_type, floor, square_meters, max_guests,
   bed_type, mattress_type, bed_comfort_notes,
   air_conditioning, refrigerator, view_and_exposure, amenities)
SELECT
  'hotel_alpha',
  (f.fl * 100 + a.pos)::text,
  a.room_type,
  f.fl,
  a.sqm,
  a.max_guests,
  a.bed_type,
  a.mattress,
  a.bed_notes,
  a.ac,
  a.fridge,
  jsonb_build_object(
    'esposizione', CASE WHEN a.pos <= 3 THEN 'Nord-Est' ELSE 'Sud-Ovest' END,
    'piano', f.fl,
    'vista', CASE
               WHEN f.fl >= 4 THEN 'Vista mare'
               WHEN f.fl = 1  THEN 'Vista giardino interno'
               ELSE 'Vista città'
             END,
    'balcone', (a.pos >= 5 OR f.fl >= 4)
  ),
  a.amenities
FROM archetipi a CROSS JOIN piani f;

-- =============================================================================
-- HOTEL ALPHA — Knowledge base (schede descrittive per la ricerca semantica)
-- Copre le categorie tipiche: ristorante, colazione, servizi, wellness,
-- strutture, policy, indicazioni. È ciò che permette al chatbot di
-- "rispondere a tutto".
-- =============================================================================
INSERT INTO knowledge_base (tenant_id, category, title, content, metadata)
VALUES
  ('hotel_alpha', 'ristorante', 'Ristorante La Terrazza — orari e prenotazioni',
   'Il ristorante interno "La Terrazza" si trova al primo piano con vista sul mare. Pranzo 12:30-14:30, cena 19:30-22:30. Cucina mediterranea con menù à la carte e opzioni vegetariane, vegane e senza glutine. Prenotazione consigliata alla reception o al numero interno 102. I bagni per gli ospiti del ristorante sono accanto all''ingresso, sulla destra.',
   '{"pranzo": "12:30-14:30", "cena": "19:30-22:30", "interno": "102", "opzioni": ["vegetariano", "vegano", "senza glutine"]}'),

  ('hotel_alpha', 'colazione', 'Colazione a buffet',
   'La colazione è servita a buffet nella sala al piano terra dalle 7:00 alle 10:30, ed è inclusa nel soggiorno. Comprende prodotti dolci e salati, cornetti, uova, affettati, formaggi, frutta fresca, yogurt, cereali, spremute, caffè e cappuccino. Sono disponibili alternative senza glutine e bevande vegetali su richiesta.',
   '{"orario": "07:00-10:30", "inclusa": true, "senza_glutine": true}'),

  ('hotel_alpha', 'servizi', 'Reception e orari di check-in / check-out',
   'La reception è aperta 24 ore su 24. Il check-in è possibile dalle 14:00, il check-out entro le 11:00. Su richiesta e in base alla disponibilità sono possibili early check-in e late check-out. È disponibile il deposito bagagli gratuito prima del check-in e dopo il check-out.',
   '{"check_in": "14:00", "check_out": "11:00", "reception_24h": true, "deposito_bagagli": true}'),

  ('hotel_alpha', 'servizi', 'Wi-Fi e connettività',
   'Il Wi-Fi ad alta velocità (fibra) è gratuito in tutte le camere e nelle aree comuni. Non serve password nelle aree comuni; in camera la rete e la password sono indicate su un cartoncino accanto al telefono. La copertura raggiunge anche la terrazza e il giardino.',
   '{"gratuito": true, "tecnologia": "fibra"}'),

  ('hotel_alpha', 'wellness', 'Spa, piscina e palestra',
   'Il centro benessere al piano -1 comprende piscina coperta riscaldata (aperta 8:00-20:00), sauna, bagno turco e una piccola palestra attrezzata (aperta 6:00-22:00). L''accesso alla piscina è incluso; sauna e bagno turco su prenotazione. I massaggi si prenotano alla reception con almeno 2 ore di anticipo.',
   '{"piscina": "08:00-20:00", "palestra": "06:00-22:00", "piscina_inclusa": true}'),

  ('hotel_alpha', 'servizi', 'Parcheggio',
   'L''hotel dispone di un parcheggio privato coperto con 20 posti auto, al costo di 15 € a notte. Sono presenti 2 colonnine di ricarica per auto elettriche (Type 2). La prenotazione del posto auto è consigliata in alta stagione. Sono disponibili posti moto gratuiti.',
   '{"coperto": true, "posti": 20, "costo_notte_eur": 15, "ricarica_ev": true}'),

  ('hotel_alpha', 'policy', 'Politica di cancellazione',
   'La cancellazione è gratuita fino a 48 ore prima della data di arrivo. Oltre questo termine, o in caso di mancata presentazione (no-show), viene addebitato l''importo della prima notte. Le tariffe non rimborsabili, se scelte in fase di prenotazione, non prevedono rimborso in caso di cancellazione.',
   '{"gratuita_entro_ore": 48, "penale": "prima notte"}'),

  ('hotel_alpha', 'policy', 'Animali domestici',
   'Gli animali domestici di piccola e media taglia (fino a 20 kg) sono benvenuti, con un supplemento di 10 € a notte per la pulizia. È richiesta la segnalazione al momento della prenotazione. Gli animali non sono ammessi nel ristorante e nell''area benessere, ad eccezione dei cani guida.',
   '{"ammessi": true, "peso_max_kg": 20, "supplemento_notte_eur": 10}'),

  ('hotel_alpha', 'strutture', 'Dove si trovano i servizi (bagni, ascensori, bar)',
   'I bagni pubblici sono al piano terra vicino alla hall e al primo piano accanto al ristorante. Gli ascensori si trovano di fronte alla reception e raggiungono tutti i piani, dal -1 (spa) al 5. Il bar "Il Molo" è nella hall, aperto dalle 10:00 a mezzanotte.',
   '{"bar": "10:00-24:00", "piani": "da -1 a 5"}'),

  ('hotel_alpha', 'indicazioni', 'Come raggiungere l''hotel',
   'L''hotel si trova in Via del Porto 15. Dalla stazione ferroviaria centrale sono 10 minuti a piedi o 5 in taxi. Dall''aeroporto, circa 25 minuti in auto; è disponibile un servizio navetta su prenotazione (25 € a tratta). Chi arriva in auto può impostare "Via del Porto 15" nel navigatore; l''ingresso del parcheggio è sul retro.',
   '{"indirizzo": "Via del Porto 15", "navetta_aeroporto_eur": 25}'),

  ('hotel_alpha', 'dintorni', 'Attrazioni e servizi nelle vicinanze',
   'Nel raggio di 500 metri si trovano il lungomare, la spiaggia attrezzata convenzionata (sconto per gli ospiti), il centro storico con negozi e ristoranti, una farmacia e un supermercato. Il molo per le escursioni in barca è a 300 metri. La reception fornisce mappe e consigli su itinerari.',
   '{"spiaggia_convenzionata": true, "raggio_metri": 500}'),

  ('hotel_alpha', 'eventi', 'Sale riunioni e piccoli eventi',
   'L''hotel dispone di una sala riunioni fino a 30 persone, con proiettore, lavagna e connessione dedicata. È possibile organizzare coffee break e light lunch. Per matrimoni e grandi eventi la terrazza panoramica è disponibile su richiesta nella bella stagione.',
   '{"sala_posti": 30, "terrazza_eventi": true}'),

  ('hotel_alpha', 'servizi', 'Servizio in camera e lavanderia',
   'Il servizio in camera è attivo dalle 7:00 alle 23:00. Il servizio di lavanderia e stireria è disponibile dal lunedì al sabato: i capi consegnati entro le 9:00 vengono riconsegnati in giornata. Su richiesta sono disponibili kit di cortesia extra, cuscini aggiuntivi e set da stiro in camera.',
   '{"room_service": "07:00-23:00", "lavanderia": "lun-sab"}'),

  ('hotel_alpha', 'policy', 'Camere per famiglie, culle e letti supplementari',
   'Le camere Triple Familiari e le Suite possono ospitare famiglie. Le culle per neonati sono gratuite e disponibili su richiesta. Il letto supplementare per un terzo/quarto ospite ha un costo di 30 € a notte, colazione inclusa. I bambini sotto i 3 anni soggiornano gratuitamente in culla.',
   '{"culla_gratuita": true, "letto_supplementare_eur": 30}');

-- =============================================================================
-- HOTEL BETA — piccolo dataset per il contrasto multi-tenant (isolamento RLS)
-- =============================================================================
INSERT INTO rooms
  (tenant_id, room_number, room_type, floor, square_meters, max_guests,
   bed_type, mattress_type, bed_comfort_notes,
   air_conditioning, refrigerator, view_and_exposure, amenities)
VALUES
  ('hotel_beta', '201', 'Suite Panoramica', 2, 45, 3,
   'Matrimoniale + Divano letto', 'Pocket Spring',
   'Suite ampia con zona living separata.',
   '{"disponibile": true, "modello": "Samsung WindFree"}',
   '{"disponibile": true, "tipo": "Frigo maggiorato", "capacita_litri": 60}',
   '{"esposizione": "Sud", "vista": "Vista collina", "balcone": true}',
   ARRAY['Wi-Fi Gratuito', 'Jacuzzi', 'Balcone']),

  ('hotel_beta', '202', 'Doppia Standard', 2, 24, 2,
   'Matrimoniale', 'Memory Foam', 'Camera doppia essenziale.',
   '{"disponibile": true, "modello": "LG Dual"}',
   '{"disponibile": true, "tipo": "Minibar", "capacita_litri": 30}',
   '{"esposizione": "Est", "vista": "Vista città", "balcone": false}',
   ARRAY['Wi-Fi Gratuito', 'TV Smart']);

INSERT INTO knowledge_base (tenant_id, category, title, content, metadata)
VALUES
  ('hotel_beta', 'eventi', 'Sale congressi',
   'Hotel Beta dispone di due sale congressi fino a 120 posti, con proiettore e impianto audio. Catering su richiesta.',
   '{"sale": 2, "posti_max": 120}'),

  ('hotel_beta', 'servizi', 'Reception',
   'La reception di Hotel Beta è aperta dalle 6:00 alle 24:00. Check-in dalle 15:00, check-out entro le 10:00.',
   '{"check_in": "15:00", "check_out": "10:00"}');

-- =============================================================================
-- BOOKING REQUESTS (una richiesta d'esempio per tenant)
-- =============================================================================
INSERT INTO booking_requests
  (tenant_id, session_id, guest_name, guest_email, guest_phone,
   room_type, check_in, check_out, num_guests, notes, status)
VALUES
  ('hotel_alpha', 'sess-alpha-001', 'Mario Rossi', 'mario.rossi@example.com', '+39 333 1112223',
   'Doppia Deluxe', '2026-07-10', '2026-07-12', 2, 'Letto supplementare se possibile.', 'pending'),

  ('hotel_beta', 'sess-beta-001', 'Giulia Bianchi', 'giulia.bianchi@example.com', NULL,
   'Suite Panoramica', '2026-08-01', '2026-08-05', 3, NULL, 'pending');

-- ---------------------------------------------------------------------------
-- TENANTS (identità hotel: API key pubblica + domini autorizzati). Valori DEV.
-- 'localhost' è incluso per poter provare il widget in locale.
-- ---------------------------------------------------------------------------
INSERT INTO tenants (tenant_id, name, reception_email, api_key, allowed_domains, active)
VALUES
  ('hotel_alpha', 'Hotel Alpha', 'reception@alpha.example.com', 'pk_alpha_dev_0001',
   ARRAY['alpha.example.com', 'www.alpha.example.com', 'localhost'], true),
  ('hotel_beta', 'Hotel Beta', 'reception@beta.example.com', 'pk_beta_dev_0002',
   ARRAY['beta.example.com', 'localhost'], true);
