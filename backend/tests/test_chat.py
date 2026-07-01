import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.main import app
from app.chat import ChatReply, answer, build_context, build_system_prompt
from app.llm import OllamaLLM, StubLLM
from app.search import SearchHit
from app.security.ratelimit import InMemoryRateLimiter
from app.sessions import InMemorySessionStore

HITS = [
    SearchHit(1, "colazione", "Colazione a buffet", "Colazione 7:00-10:30, inclusa.", None, 0.9),
    SearchHit(2, "servizi", "Reception", "Aperta 24h.", None, 0.6),
]


def _search_fn(hits):
    def fn(tenant_id, query, k):
        return hits[:k]
    return fn


# --- orchestrazione (offline) ----------------------------------------------

def test_build_context_empty():
    assert "nessuna informazione" in build_context([])


def test_build_system_prompt_includes_titles():
    p = build_system_prompt(HITS)
    assert "Colazione a buffet" in p
    assert "CONTESTO" in p


def test_answer_flow():
    store = InMemorySessionStore()
    reply = answer(_search_fn(HITS), store, StubLLM(), "hotel_alpha", "s1", "a che ora la colazione?")
    assert isinstance(reply, ChatReply)
    assert "[stub]" in reply.reply
    assert reply.sources == ["Colazione a buffet", "Reception"]
    # storia: utente + assistente salvati
    hist = store.history("hotel_alpha", "s1")
    assert [m["role"] for m in hist] == ["user", "assistant"]


def test_answer_grounds_on_context_via_stub():
    # Lo StubLLM riflette l'ultimo messaggio utente: verifica il passaggio dati.
    store = InMemorySessionStore()
    reply = answer(_search_fn([]), store, StubLLM(), "t", "s", "domanda X")
    assert "domanda X" in reply.reply
    assert reply.sources == []


# --- OllamaLLM con trasporto finto -----------------------------------------

def test_ollama_llm_parses_message():
    def handler(req):
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "ciao!"}})
    llm = OllamaLLM("http://x", "llama3", transport=httpx.MockTransport(handler))
    assert llm.generate("sys", [{"role": "user", "content": "hi"}]) == "ciao!"


def test_ollama_llm_malformed_raises():
    def handler(req):
        return httpx.Response(200, json={"nope": 1})
    llm = OllamaLLM("http://x", "llama3", transport=httpx.MockTransport(handler))
    with pytest.raises(ValueError):
        llm.generate("sys", [{"role": "user", "content": "hi"}])


# --- endpoint /api/chat -----------------------------------------------------

@pytest.fixture
def client():
    def fake_chat_service():
        store = InMemorySessionStore()

        def service(tenant_id, session_id, message):
            return answer(_search_fn(HITS), store, StubLLM(), tenant_id, session_id, message)

        return service

    app.dependency_overrides[deps.require_session] = lambda: {"tenant_id": "hotel_alpha", "sid": "s1"}
    app.dependency_overrides[deps.get_chat_service] = fake_chat_service
    app.dependency_overrides[deps.get_rate_limiter] = lambda: InMemoryRateLimiter(100, 60)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_chat_endpoint(client):
    r = client.post("/api/chat", json={"message": "a che ora la colazione?"},
                    headers={"Authorization": "Bearer x"})
    assert r.status_code == 200
    data = r.json()
    assert "[stub]" in data["reply"]
    assert "Colazione a buffet" in data["sources"]


def test_chat_validation_empty(client):
    r = client.post("/api/chat", json={"message": ""}, headers={"Authorization": "Bearer x"})
    assert r.status_code == 422


def test_chat_requires_token():
    c = TestClient(app)
    assert c.post("/api/chat", json={"message": "x"}).status_code == 401
