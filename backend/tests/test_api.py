import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.main import app
from app.search import SearchHit
from app.security.ratelimit import InMemoryRateLimiter
from app.security.tenants import Tenant

TENANT = Tenant("hotel_alpha", "Hotel Alpha", ["alpha.example.com", "localhost"], True)
GOOD = {"X-API-Key": "good_key", "Origin": "https://alpha.example.com"}


def _resolver():
    def resolver(api_key):
        return TENANT if api_key == "good_key" else None
    return resolver


def _searcher():
    def searcher(tenant_id, query, k):
        hits = [
            SearchHit(1, "colazione", "Colazione a buffet", "Colazione 7:00-10:30", None, 0.91),
            SearchHit(2, "servizi", "Reception", "Aperta 24h", None, 0.70),
        ]
        return hits[:k]
    return searcher


@pytest.fixture
def client():
    limiter = InMemoryRateLimiter(limit=100, window_seconds=60)
    app.dependency_overrides[deps.get_tenant_resolver] = _resolver
    app.dependency_overrides[deps.get_rate_limiter] = lambda: limiter
    app.dependency_overrides[deps.get_searcher] = _searcher
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_session_missing_api_key(client):
    r = client.post("/api/session", headers={"Origin": "https://alpha.example.com"})
    assert r.status_code == 401


def test_session_unknown_api_key(client):
    r = client.post("/api/session", headers={"X-API-Key": "nope", "Origin": "https://alpha.example.com"})
    assert r.status_code == 401


def test_session_bad_origin(client):
    r = client.post("/api/session", headers={"X-API-Key": "good_key", "Origin": "https://evil.com"})
    assert r.status_code == 403


def test_session_happy(client):
    r = client.post("/api/session", headers=GOOD)
    assert r.status_code == 200
    body = r.json()
    assert body["token"]
    assert body["expires_in"] > 0


def test_search_requires_token(client):
    r = client.post("/api/search", json={"query": "colazione"})
    assert r.status_code == 401


def test_search_invalid_token(client):
    r = client.post(
        "/api/search", json={"query": "x"}, headers={"Authorization": "Bearer not.a.token"}
    )
    assert r.status_code == 401


def test_search_end_to_end(client):
    token = client.post("/api/session", headers=GOOD).json()["token"]
    r = client.post(
        "/api/search",
        json={"query": "a che ora è la colazione?", "k": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["tenant_id"] == "hotel_alpha"
    assert len(data["hits"]) == 2
    assert data["hits"][0]["title"] == "Colazione a buffet"


def test_search_validation_empty_query(client):
    token = client.post("/api/session", headers=GOOD).json()["token"]
    r = client.post(
        "/api/search", json={"query": ""}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 422


def test_rate_limit_blocks_second_session():
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
    app.dependency_overrides[deps.get_tenant_resolver] = _resolver
    app.dependency_overrides[deps.get_rate_limiter] = lambda: limiter
    try:
        c = TestClient(app)
        assert c.post("/api/session", headers=GOOD).status_code == 200
        assert c.post("/api/session", headers=GOOD).status_code == 429
    finally:
        app.dependency_overrides.clear()
