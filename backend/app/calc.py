"""
Calcoli DETERMINISTICI fatti dal backend, non dall'IA.

Regola d'oro anti-allucinazione: numeri, conversioni, prezzi e durate li calcola
il backend e li passa già pronti all'IA, che li riporta soltanto. Qui stanno le
funzioni pure (facilmente testabili) per farlo.
"""
from __future__ import annotations

from datetime import date
from typing import Union

DateLike = Union[date, str]


def celsius_to_kelvin(c: float) -> float:
    return round(c + 273.15, 2)


def kelvin_to_celsius(k: float) -> float:
    return round(k - 273.15, 2)


def celsius_to_fahrenheit(c: float) -> float:
    return round(c * 9 / 5 + 32, 2)


def _as_date(d: DateLike) -> date:
    return d if isinstance(d, date) else date.fromisoformat(d)


def nights_between(check_in: DateLike, check_out: DateLike) -> int:
    """Numero di notti tra check-in e check-out. Solleva se check_out <= check_in."""
    ci, co = _as_date(check_in), _as_date(check_out)
    nights = (co - ci).days
    if nights <= 0:
        raise ValueError("check_out deve essere successivo a check_in")
    return nights


def format_price_eur(amount: float) -> str:
    """Formatta un importo in stile italiano: 1.234,56 €."""
    s = f"{amount:,.2f}"  # es. '1,234.56' (stile US)
    s = s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return f"{s} €"


def total_price(price_per_night: float, check_in: DateLike, check_out: DateLike) -> float:
    """Prezzo totale = prezzo/notte × numero di notti (calcolato dal backend)."""
    return round(price_per_night * nights_between(check_in, check_out), 2)
