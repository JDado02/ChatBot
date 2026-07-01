"""
Richiesta di prenotazione raccolta dal chatbot.

NON è una conferma automatica: si salva una richiesta con stato 'pending' in
`booking_requests` e si avvisa la reception via email; sarà la reception a
confermare all'utente. Va comunicato chiaramente per non creare false aspettative.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .calc import nights_between
from .db import tenant_transaction

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class BookingInput:
    guest_name: str
    guest_email: str
    check_in: str  # ISO 'YYYY-MM-DD'
    check_out: str
    num_guests: int
    guest_phone: Optional[str] = None
    room_type: Optional[str] = None
    notes: Optional[str] = None


def validate_booking(b: BookingInput) -> None:
    """Validazioni di base. Solleva ValueError con messaggio chiaro."""
    if not b.guest_name.strip():
        raise ValueError("nome ospite obbligatorio")
    if not _EMAIL_RE.match(b.guest_email or ""):
        raise ValueError("email non valida")
    if b.num_guests < 1:
        raise ValueError("numero ospiti deve essere >= 1")
    # nights_between solleva se check_out <= check_in o date malformate
    nights_between(b.check_in, b.check_out)


def create_booking(conn, tenant_id: str, session_id: str, b: BookingInput) -> int:
    """Valida e salva la richiesta (stato 'pending'). Ritorna l'id creato.

    tenant_id viene inserito esplicitamente e coincide con app.current_tenant:
    la policy RLS WITH CHECK lo consente (non si può creare per un altro hotel).
    """
    validate_booking(b)
    with tenant_transaction(conn, tenant_id) as c:
        row = c.execute(
            "INSERT INTO booking_requests "
            "(tenant_id, session_id, guest_name, guest_email, guest_phone, "
            " room_type, check_in, check_out, num_guests, notes) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (
                tenant_id, session_id, b.guest_name, b.guest_email, b.guest_phone,
                b.room_type, b.check_in, b.check_out, b.num_guests, b.notes,
            ),
        ).fetchone()
    return int(row[0])
