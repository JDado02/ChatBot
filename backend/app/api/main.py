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

from fastapi import Depends, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..booking import BookingInput
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


# --- /api/rooms -------------------------------------------------------------
class RoomOut(BaseModel):
    room_number: str
    room_type: str
    floor: int
    square_meters: int
    max_guests: int
    bed_type: str
    amenities: List[str]
    air_conditioning: Optional[dict] = None
    refrigerator: Optional[dict] = None
    view_and_exposure: Optional[dict] = None


@app.get("/api/rooms", response_model=List[RoomOut])
def rooms_list(
    session: dict = Depends(deps.require_session),
    reader=Depends(deps.get_room_reader),
    limiter=Depends(deps.get_rate_limiter),
) -> List[RoomOut]:
    tenant_id = session["tenant_id"]
    deps.enforce_rate_limit(f"rooms:{tenant_id}", limiter)
    return [RoomOut(**vars(r)) for r in reader.list(tenant_id)]


@app.get("/api/rooms/{room_number}", response_model=RoomOut)
def rooms_get(
    room_number: str,
    session: dict = Depends(deps.require_session),
    reader=Depends(deps.get_room_reader),
) -> RoomOut:
    room = reader.get(session["tenant_id"], room_number)
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "stanza non trovata")
    return RoomOut(**vars(room))


# --- /api/chat --------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    reply: str
    sources: List[str]


@app.post("/api/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    session: dict = Depends(deps.require_session),
    chat_service=Depends(deps.get_chat_service),
    limiter=Depends(deps.get_rate_limiter),
) -> ChatResponse:
    tenant_id = session["tenant_id"]
    deps.enforce_rate_limit(f"chat:{tenant_id}", limiter)
    # Il session_id della conversazione è quello dentro il token (sid): così la
    # storia è legata alla sessione emessa, non a un input arbitrario del client.
    result = chat_service(tenant_id, session["sid"], body.message)
    return ChatResponse(reply=result.reply, sources=result.sources)


# --- /api/booking -----------------------------------------------------------
class BookingBody(BaseModel):
    guest_name: str = Field(min_length=1, max_length=120)
    guest_email: str = Field(min_length=3, max_length=160)
    check_in: str
    check_out: str
    num_guests: int = Field(ge=1, le=20)
    guest_phone: Optional[str] = Field(default=None, max_length=40)
    room_type: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=1000)


class BookingResponse(BaseModel):
    booking_id: int
    status: str
    message: str


@app.post("/api/booking", response_model=BookingResponse)
def create_booking_endpoint(
    body: BookingBody,
    session: dict = Depends(deps.require_session),
    booking_service=Depends(deps.get_booking_service),
    limiter=Depends(deps.get_rate_limiter),
) -> BookingResponse:
    tenant_id = session["tenant_id"]
    deps.enforce_rate_limit(f"booking:{tenant_id}", limiter)
    booking = BookingInput(
        guest_name=body.guest_name,
        guest_email=body.guest_email,
        check_in=body.check_in,
        check_out=body.check_out,
        num_guests=body.num_guests,
        guest_phone=body.guest_phone,
        room_type=body.room_type,
        notes=body.notes,
    )
    try:
        booking_id = booking_service(tenant_id, session["sid"], booking)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    return BookingResponse(
        booking_id=booking_id,
        status="pending",
        message="Richiesta inviata alla reception. Riceverai conferma via email.",
    )
