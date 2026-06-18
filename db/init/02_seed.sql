-- =============================================================================
-- 02_seed.sql
-- Dati di test per due hotel fittizi: 'hotel_alpha' e 'hotel_beta'.
-- Servono a verificare l'isolamento multi-tenant (vedi db/test/).
--
-- Eseguito come SUPERUSER durante l'init: il superuser bypassa la RLS, quindi
-- può inserire righe per entrambi i tenant. È esattamente ciò che vogliamo per
-- popolare i dati di seed. Il backend, invece, userà 'app_user' e vedrà solo
-- il proprio tenant.
--
-- NOTA: il campo 'embedding' è lasciato NULL. Gli embedding reali vengono
-- generati dal modello locale nella pipeline applicativa (passo successivo).
-- Per il test di isolamento non servono.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- ROOMS
-- ---------------------------------------------------------------------------
INSERT INTO rooms
  (tenant_id, room_number, room_type, floor, square_meters, max_guests,
   bed_type, mattress_type, bed_comfort_notes,
   air_conditioning, refrigerator, amenities)
VALUES
  ('hotel_alpha', '101', 'Doppia Deluxe', 1, 28, 2,
   'Matrimoniale King Size', 'Memory Foam ortopedico',
   'Letto regolabile, due cuscini in piuma e due in memory.',
   '{"disponibile": true, "modello": "Daikin Silent 2026", "range_temperatura": {"min_celsius": 16, "max_celsius": 30}}',
   '{"disponibile": true, "tipo": "Minibar", "capacita_litri": 45, "ha_congelatore": true}',
   ARRAY['Wi-Fi Gratuito', 'Cassaforte', 'Vista mare']),

  ('hotel_alpha', '102', 'Singola Comfort', 1, 18, 1,
   'Singola', 'Lattice', 'Materasso ergonomico singolo.',
   '{"disponibile": true, "modello": "Mitsubishi Eco"}',
   '{"disponibile": false}',
   ARRAY['Wi-Fi Gratuito', 'Scrivania']),

  ('hotel_beta', '201', 'Suite Panoramica', 2, 45, 3,
   'Matrimoniale + Divano letto', 'Pocket Spring',
   'Suite ampia con zona living separata.',
   '{"disponibile": true, "modello": "Samsung WindFree"}',
   '{"disponibile": true, "tipo": "Frigo maggiorato", "capacita_litri": 60}',
   ARRAY['Wi-Fi Gratuito', 'Jacuzzi', 'Balcone']);

-- ---------------------------------------------------------------------------
-- KNOWLEDGE BASE
-- ---------------------------------------------------------------------------
INSERT INTO knowledge_base (tenant_id, category, title, content, metadata)
VALUES
  ('hotel_alpha', 'ristorante', 'Orari del ristorante',
   'Il ristorante "La Terrazza" è al primo piano. Colazione 7:00-10:30 a buffet, inclusa. Cena 19:30-22:30. Prenotazione consigliata al numero interno 102.',
   '{"colazione": "07:00-10:30", "cena": "19:30-22:30"}'),

  ('hotel_alpha', 'servizi', 'Reception e check-in',
   'La reception è aperta 24 ore su 24. Check-in dalle 14:00, check-out entro le 11:00. Deposito bagagli gratuito.',
   '{"check_in": "14:00", "check_out": "11:00"}'),

  ('hotel_beta', 'eventi', 'Eventi e congressi',
   'Hotel Beta dispone di due sale congressi fino a 120 posti, con proiettore e impianto audio. Catering su richiesta.',
   '{"sale": 2, "posti_max": 120}');

-- ---------------------------------------------------------------------------
-- BOOKING REQUESTS (una richiesta d'esempio per tenant)
-- ---------------------------------------------------------------------------
INSERT INTO booking_requests
  (tenant_id, session_id, guest_name, guest_email, guest_phone,
   room_type, check_in, check_out, num_guests, notes, status)
VALUES
  ('hotel_alpha', 'sess-alpha-001', 'Mario Rossi', 'mario.rossi@example.com', '+39 333 1112223',
   'Doppia Deluxe', '2026-07-10', '2026-07-12', 2, 'Letto supplementare se possibile.', 'pending'),

  ('hotel_beta', 'sess-beta-001', 'Giulia Bianchi', 'giulia.bianchi@example.com', NULL,
   'Suite Panoramica', '2026-08-01', '2026-08-05', 3, NULL, 'pending');
