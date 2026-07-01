"""
Dipendenze FastAPI: identificazione tenant, allowlist, rate limit, token.

I "provider" (resolver del tenant, searcher, rate limiter, segreto) sono
funzioni sostituibili nei test tramite `app.dependency_overrides`, così gli
endpoint si testano senza DB/modello reali.
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status

from ..config import settings
from ..security.allowlist import is_origin_allowed
from ..security.ratelimit import InMemoryRateLimiter
from ..security.tenants import Tenant
from ..security.tokens import TokenError, verify_token


# --------------------------------------------------------------------------
# Provider (override-abili nei test)
# --------------------------------------------------------------------------
def get_tenant_resolver():
    """Ritorna una funzione api_key -> Tenant|None (implementazione con DB)."""
    from ..db import connect
    from ..security.tenants import get_tenant_by_api_key

    def resolver(api_key: str) -> Optional[Tenant]:
        with connect() as conn:
            return get_tenant_by_api_key(conn, api_key)

    return resolver


def get_searcher():
    """Ritorna una funzione (tenant_id, query, k) -> list[SearchHit] (con DB+modello)."""
    from ..db import connect
    from ..embeddings import build_default_embedder
    from ..search import semantic_search

    embedder = build_default_embedder(settings)

    def searcher(tenant_id: str, query: str, k: int):
        with connect() as conn:
            return semantic_search(conn, tenant_id, query, embedder, k=k)

    return searcher


def get_room_reader():
    """Ritorna un oggetto con .list(tenant_id) e .get(tenant_id, room_number)."""
    from ..db import connect
    from .. import rooms as rooms_mod

    class _Reader:
        def list(self, tenant_id: str):
            with connect() as conn:
                return rooms_mod.list_rooms(conn, tenant_id)

        def get(self, tenant_id: str, room_number: str):
            with connect() as conn:
                return rooms_mod.get_room(conn, tenant_id, room_number)

    return _Reader()


def get_chat_service():
    """Ritorna una funzione (tenant_id, session_id, message) -> ChatReply che
    orchestra RAG + memoria Redis + LLM. Nei test si sostituisce con un fake."""
    from ..chat import answer
    from ..db import connect
    from ..embeddings import build_default_embedder
    from ..llm import OllamaLLM
    from ..search import semantic_search
    from ..sessions import RedisSessionStore

    embedder = build_default_embedder(settings)
    llm = OllamaLLM(settings.ollama_url, settings.chat_model)

    def search_fn(tenant_id: str, query: str, k: int):
        with connect() as conn:
            return semantic_search(conn, tenant_id, query, embedder, k=k)

    def service(tenant_id: str, session_id: str, message: str):
        import redis  # dipendenza runtime (lazy)

        r = redis.Redis(
            host=settings.redis_host, port=settings.redis_port, decode_responses=True
        )
        store = RedisSessionStore(r, ttl_seconds=settings.conversation_ttl_seconds)
        return answer(search_fn, store, llm, tenant_id, session_id, message)

    return service


def get_booking_service():
    """Ritorna una funzione (tenant_id, session_id, BookingInput) -> booking_id
    che salva la richiesta e avvisa la reception via email. Fake nei test."""
    from ..booking import create_booking
    from ..db import connect
    from ..email import StubEmailSender, format_booking_email
    from ..security.tenants import get_tenant_contact

    # In dev: StubEmailSender (registra, non invia). In prod: SmtpEmailSender
    # configurato via env (vedi email.py). Sostituibile nei test.
    sender = StubEmailSender()

    def service(tenant_id: str, session_id: str, booking):
        with connect() as conn:
            booking_id = create_booking(conn, tenant_id, session_id, booking)
            contact = get_tenant_contact(conn, tenant_id)
        name = contact[0] if contact else tenant_id
        reception_email = contact[1] if contact else None
        if reception_email:
            subject, body = format_booking_email(name, booking, booking_id)
            sender.send(reception_email, subject, body)
        return booking_id

    return service


_rate_limiter = InMemoryRateLimiter(settings.rate_limit, settings.rate_window_seconds)


def get_rate_limiter() -> InMemoryRateLimiter:
    return _rate_limiter


def get_token_secret() -> str:
    return settings.session_secret


# --------------------------------------------------------------------------
# Dipendenze usate dagli endpoint
# --------------------------------------------------------------------------
def require_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    if not x_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "API key mancante")
    return x_api_key


def resolve_tenant(
    api_key: str = Depends(require_api_key),
    resolver=Depends(get_tenant_resolver),
) -> Tenant:
    tenant = resolver(api_key)
    if tenant is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "API key non valida o disattivata")
    return tenant


def check_allowlist(request: Request, tenant: Tenant = Depends(resolve_tenant)) -> Tenant:
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    if not is_origin_allowed(origin, referer, tenant.allowed_domains):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "dominio non autorizzato")
    return tenant


def enforce_rate_limit(key: str, limiter: InMemoryRateLimiter) -> None:
    if not limiter.allow(key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "troppe richieste")


def require_session(
    authorization: Optional[str] = Header(None),
    secret: str = Depends(get_token_secret),
) -> dict:
    """Verifica il token di sessione (header Authorization: Bearer <token>)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token di sessione mancante")
    token = authorization[7:].strip()
    try:
        return verify_token(token, secret)
    except TokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"token non valido: {exc}")
