import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.main import app
from app.rooms import Room, _row_to_room
from app.security.ratelimit import InMemoryRateLimiter

ROOMS = [
    Room("101", "Doppia Deluxe", 1, 28, 2, "King Size",
         ["Wi-Fi", "Cassaforte"], {"disponibile": True}, {"disponibile": True}, {"vista": "mare"}),
    Room("102", "Singola Comfort", 1, 18, 1, "Singola",
         ["Wi-Fi"], None, {"disponibile": False}, None),
]


def test_row_to_room_maps_null_amenities():
    r = _row_to_room(("201", "Suite", 2, 45, 3, "King", None, None, None, None))
    assert r.room_number == "201"
    assert r.amenities == []


class FakeReader:
    def list(self, tenant_id):
        return ROOMS

    def get(self, tenant_id, number):
        return next((r for r in ROOMS if r.room_number == number), None)


@pytest.fixture
def client():
    app.dependency_overrides[deps.require_session] = lambda: {"tenant_id": "hotel_alpha", "sid": "s1"}
    app.dependency_overrides[deps.get_room_reader] = lambda: FakeReader()
    app.dependency_overrides[deps.get_rate_limiter] = lambda: InMemoryRateLimiter(100, 60)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_rooms(client):
    r = client.get("/api/rooms", headers={"Authorization": "Bearer x"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["room_number"] == "101"
    assert data[0]["view_and_exposure"] == {"vista": "mare"}


def test_get_room(client):
    r = client.get("/api/rooms/102", headers={"Authorization": "Bearer x"})
    assert r.status_code == 200
    assert r.json()["room_type"] == "Singola Comfort"


def test_get_room_not_found(client):
    r = client.get("/api/rooms/999", headers={"Authorization": "Bearer x"})
    assert r.status_code == 404


def test_rooms_require_token():
    # nessun override di require_session: senza token deve dare 401
    c = TestClient(app)
    assert c.get("/api/rooms").status_code == 401
