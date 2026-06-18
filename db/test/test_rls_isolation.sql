-- =============================================================================
-- test_rls_isolation.sql
-- Verifica che la Row-Level Security isoli davvero i tenant.
-- Va eseguito CONNESSI COME 'app_user' (NON come superuser, che bypassa la RLS).
--
-- Esito atteso: ogni asserzione stampa 'PASS'. Se qualcosa è 'FAIL' o lo script
-- si interrompe con errore, l'isolamento NON è garantito.
-- =============================================================================

\echo '== Conferma: NON dobbiamo essere superuser =='
SELECT rolname, rolsuper FROM pg_roles WHERE rolname = current_user;

-- ---------------------------------------------------------------------------
-- TEST 1: senza tenant impostato -> non si vede NULLA (fail-safe)
-- ---------------------------------------------------------------------------
\echo ''
\echo '== TEST 1: nessun tenant impostato => 0 righe visibili =='
DO $$
DECLARE n INT;
BEGIN
  SELECT count(*) INTO n FROM rooms;
  IF n = 0 THEN RAISE NOTICE 'PASS: senza tenant vedo 0 stanze';
  ELSE RAISE EXCEPTION 'FAIL: senza tenant vedo % stanze (atteso 0)', n;
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- TEST 2: come hotel_alpha vedo SOLO i dati di hotel_alpha
-- ---------------------------------------------------------------------------
\echo ''
\echo '== TEST 2: tenant = hotel_alpha =='
SET app.current_tenant = 'hotel_alpha';
DO $$
DECLARE mine INT; others INT;
BEGIN
  SELECT count(*) INTO mine   FROM rooms WHERE tenant_id = 'hotel_alpha';
  SELECT count(*) INTO others FROM rooms WHERE tenant_id <> 'hotel_alpha';
  IF mine > 0 AND others = 0 THEN
    RAISE NOTICE 'PASS: vedo % stanze alpha, 0 di altri hotel', mine;
  ELSE
    RAISE EXCEPTION 'FAIL: alpha=%, altri=% (atteso altri=0)', mine, others;
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- TEST 3: come hotel_beta vedo SOLO i dati di hotel_beta
-- ---------------------------------------------------------------------------
\echo ''
\echo '== TEST 3: tenant = hotel_beta =='
SET app.current_tenant = 'hotel_beta';
DO $$
DECLARE mine INT; others INT;
BEGIN
  SELECT count(*) INTO mine   FROM knowledge_base WHERE tenant_id = 'hotel_beta';
  SELECT count(*) INTO others FROM knowledge_base WHERE tenant_id <> 'hotel_beta';
  IF mine > 0 AND others = 0 THEN
    RAISE NOTICE 'PASS: vedo % schede beta, 0 di altri hotel', mine;
  ELSE
    RAISE EXCEPTION 'FAIL: beta=%, altri=% (atteso altri=0)', mine, others;
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- TEST 4: WITH CHECK impedisce di inserire righe per un ALTRO tenant
-- (sono hotel_beta e provo a scrivere come hotel_alpha -> deve fallire)
-- ---------------------------------------------------------------------------
\echo ''
\echo '== TEST 4: insert cross-tenant deve essere RIFIUTATO =='
DO $$
BEGIN
  BEGIN
    INSERT INTO rooms (tenant_id, room_number, room_type, floor, square_meters, max_guests, bed_type)
    VALUES ('hotel_alpha', '999', 'Hack', 9, 10, 1, 'Singola');
    RAISE EXCEPTION 'FAIL: inserimento cross-tenant riuscito (NON doveva)';
  EXCEPTION WHEN insufficient_privilege OR check_violation THEN
    RAISE NOTICE 'PASS: insert cross-tenant correttamente rifiutato';
  END;
END $$;

\echo ''
\echo '== TUTTI I TEST SUPERATI =='
