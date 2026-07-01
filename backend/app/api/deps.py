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
