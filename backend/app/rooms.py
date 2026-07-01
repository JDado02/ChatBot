"""
Lettura dei dati strutturati delle stanze, isolata per tenant dalla RLS.

Serve al chatbot per rispondere su dettagli iper-specifici delle camere
(condizionatore, frigo, vista…) prendendo i dati precisi dal DB invece di
lasciarli "inventare" all'IA.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .db import tenant_transaction

_COLS = (
    "room_number, room_type, floor, square_meters, max_guests, bed_type, "
    "amenities, air_conditioning, refrigerator, view_and_exposure"
)


@dataclass
class Room:
    room_number: str
    room_type: str
    floor: int
    square_meters: int
    max_guests: int
    bed_type: str
    amenities: List[str]
    air_conditioning: Optional[dict]
    refrigerator: Optional[dict]
    view_and_exposure: Optional[dict]


def _row_to_room(r) -> Room:
    return Room(
        room_number=r[0],
        room_type=r[1],
        floor=r[2],
        square_meters=r[3],
        max_guests=r[4],
        bed_type=r[5],
        amenities=list(r[6] or []),
        air_conditioning=r[7],
        refrigerator=r[8],
        view_and_exposure=r[9],
    )


def list_rooms(conn, tenant_id: str) -> List[Room]:
    with tenant_transaction(conn, tenant_id) as c:
        rows = c.execute(f"SELECT {_COLS} FROM rooms ORDER BY room_number").fetchall()
    return [_row_to_room(r) for r in rows]


def get_room(conn, tenant_id: str, room_number: str) -> Optional[Room]:
    with tenant_transaction(conn, tenant_id) as c:
        row = c.execute(
            f"SELECT {_COLS} FROM rooms WHERE room_number = %s", (room_number,)
        ).fetchone()
    return _row_to_room(row) if row else None
