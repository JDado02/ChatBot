"""
Adapter PMS (gestionale dell'hotel) — interfaccia comune.

Il resto del sistema parla sempre lo stesso "linguaggio" (`get_availability`,
`get_price`); dietro, ogni hotel ha il suo connettore su misura (API dirette,
channel manager, file, o niente). Le implementazioni reali sono per-cliente e si
scrivono in fase di sopralluogo; qui ci sono l'interfaccia e due adapter base.

Convenzione: `None` = "non disponibile / non so" (es. PMS senza automazione).
In quel caso il chatbot risponde "verifichiamo e la ricontattiamo".
"""
from __future__ import annotations

from typing import Optional, Protocol


class PMSAdapter(Protocol):
    def get_availability(self, room_type: str, check_in: str, check_out: str) -> Optional[bool]: ...
    def get_price(self, room_type: str, check_in: str, check_out: str) -> Optional[float]: ...


class NullPMS:
    """Nessuna automazione possibile: non conosce disponibilità né prezzo."""

    def get_availability(self, room_type, check_in, check_out) -> Optional[bool]:
        return None

    def get_price(self, room_type, check_in, check_out) -> Optional[float]:
        return None


class FakePMS:
    """PMS finto per dev/test: risposte prefissate."""

    def __init__(self, available: Optional[bool] = True, price: Optional[float] = 120.0) -> None:
        self._available = available
        self._price = price

    def get_availability(self, room_type, check_in, check_out) -> Optional[bool]:
        return self._available

    def get_price(self, room_type, check_in, check_out) -> Optional[float]:
        return self._price
