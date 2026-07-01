"""
App FastAPI dell'AI Concierge (Passo 6, slice 1).

Endpoint:
- GET  /health          liveness
- POST /api/session     bootstrap: verifica API key + dominio + rate limit,
                        emette un token di sessione a vita breve
- POST /api/search      ricerca semantica (RAG) sulla knowledge base del tenant;
                        richiede un token di sessione valido

La catena di sicurezza (API key -> tenant -> allowlist -> rate limit -> token)
riusa i moduli del Passo 5. La chat con LLM e la storia conversazione su Redis
arrivano nel prossimo slice.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel, Field

from ..config import settings
from ..security.tenants import Tenant
from ..security.tokens import issue_token
from . import deps

app = FastAPI(title="AI Concierge API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# --- /api/session -----------------------------------------------------------
class SessionResponse(BaseModel):
    token: str
    expires_in: int


@app.post("/api/session", response_model=SessionResponse)
def create_session(
    request: Request,
    tenant: Tenant = Depends(deps.check_allowlist),
    limiter=Depends(deps.get_rate_limiter),
) -> SessionResponse:
    deps.enforce_rate_limit(f"session:{tenant.tenant_id}", limiter)
    sid = uuid.uuid4().hex
    token = issue_token(
        {"tenant_id": tenant.tenant_id, "sid": sid},
        settings.session_secret,
        ttl_seconds=settings.session_ttl_seconds,
    )
    return SessionResponse(token=token, expires_in=settings.session_ttl_seconds)


# --- /api/search ------------------------------------------------------------
class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    k: int = Field(default=5, ge=1, le=20)


class SearchHitOut(BaseModel):
    id: int
    category: str
    title: str
    content: str
    score: float


class SearchResponse(BaseModel):
    tenant_id: str
    hits: List[SearchHitOut]


@app.post("/api/search", response_model=SearchResponse)
def search(
    body: SearchRequest,
    session: dict = Depends(deps.require_session),
    searcher=Depends(deps.get_searcher),
    limiter=Depends(deps.get_rate_limiter),
) -> SearchResponse:
    tenant_id = session["tenant_id"]
    deps.enforce_rate_limit(f"search:{tenant_id}", limiter)
    hits = searcher(tenant_id, body.query, body.k)
    return SearchResponse(
        tenant_id=tenant_id,
        hits=[
            SearchHitOut(
                id=h.id, category=h.category, title=h.title, content=h.content, score=h.score
            )
            for h in hits
        ],
    )
