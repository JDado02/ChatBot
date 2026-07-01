import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.main import app
from app.booking import BookingInput, create_booking, validate_booking
from app.email import StubEmailSender, format_booking_email
from app.pms import FakePMS, NullPMS
from app.security.ratelimit import InMemoryRateLimiter

VALID = BookingInput(
    guest_name="Mario Rossi", guest_email="mario@example.com",
    check_in="2026-07-10", check_out="2026-07-12", num_guests=2, room_type="Doppia",
)


# --- validazione ------------------------------------------------------------

def test_validate_ok():
    validate_booking(VALID)  # non solleva


def test_validate_bad_email():
    b = BookingInput("Mario", "non-una-email", "2026-07-10", "2026-07-12", 2)
    with pytest.raises(ValueError):
        validate_booking(b)


def test_validate_zero_guests():
    b = BookingInput("Mario", "m@x.it", "2026-07-10", "2026-07-12", 0)
    with pytest.raises(ValueError):
        validate_booking(b)


def test_validate_dates_inverted():
    b = BookingInput("Mario", "m@x.it", "2026-07-12", "2026-07-10", 2)
    with pytest.raises(ValueError):
        validate_booking(b)


# --- create_booking con connessione finta -----------------------------------

class FakeCursor:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class FakeConn:
    def __init__(self, insert_id=99):
        self.calls = []
        self._id = insert_id

    def transaction(self):
        conn = self

        class _Tx:
            def __enter__(self_):
                return conn

            def __exit__(self_, *a):
                return False

        return _Tx()

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        return FakeCursor((self._id,))


def test_create_booking_inserts_and_returns_id():
    conn = FakeConn(insert_id=42)
    bid = create_booking(conn, "hotel_alpha", "sess1", VALID)
    assert bid == 42
    # set_config col tenant + INSERT su booking_requests
    assert any("set_config" in sql for sql, _ in conn.calls)
    insert = [c for c in conn.calls if "INSERT INTO booking_requests" in c[0]]
    assert insert and insert[0][1][0] == "hotel_alpha"  # tenant_id come primo param


# --- email + PMS ------------------------------------------------------------

def test_format_booking_email():
    subject, body = format_booking_email("Hotel Alpha", VALID, 7)
    assert "#7" in subject and "Hotel Alpha" in subject
    assert "Mario Rossi" in body
    assert "Notti: 2" in body


def test_stub_email_sender_records():
    s = StubEmailSender()
    s.send("reception@x.it", "sub", "body")
    assert s.sent == [{"to": "reception@x.it", "subject": "sub", "body": "body"}]


def test_pms_fakes():
    assert FakePMS(available=True, price=100.0).get_price("Doppia", "a", "b") == 100.0
    assert NullPMS().get_availability("Doppia", "a", "b") is None


# --- endpoint ---------------------------------------------------------------

@pytest.fixture
def client():
    recorded = {}

    def fake_service():
        def service(tenant_id, session_id, booking):
            recorded["booking"] = booking
            recorded["tenant"] = tenant_id
            return 123
        return service

    app.dependency_overrides[deps.require_session] = lambda: {"tenant_id": "hotel_alpha", "sid": "s1"}
    app.dependency_overrides[deps.get_booking_service] = fake_service
    app.dependency_overrides[deps.get_rate_limiter] = lambda: InMemoryRateLimiter(100, 60)
    c = TestClient(app)
    c._recorded = recorded
    yield c
    app.dependency_overrides.clear()


def test_booking_endpoint_happy(client):
    r = client.post(
        "/api/booking",
        json={
            "guest_name": "Mario Rossi", "guest_email": "mario@example.com",
            "check_in": "2026-07-10", "check_out": "2026-07-12", "num_guests": 2,
        },
        headers={"Authorization": "Bearer x"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["booking_id"] == 123
    assert data["status"] == "pending"
    assert client._recorded["tenant"] == "hotel_alpha"


def test_booking_endpoint_validation(client):
    r = client.post(
        "/api/booking",
        json={
            "guest_name": "Mario", "guest_email": "m@x.it",
            "check_in": "2026-07-10", "check_out": "2026-07-12", "num_guests": 0,
        },
        headers={"Authorization": "Bearer x"},
    )
    assert r.status_code == 422


def test_booking_requires_token():
    c = TestClient(app)
    r = c.post("/api/booking", json={
        "guest_name": "M", "guest_email": "m@x.it",
        "check_in": "2026-07-10", "check_out": "2026-07-12", "num_guests": 1,
    })
    assert r.status_code == 401
