"""
Governance delle risposte: system prompt anti-allucinazione + costruzione del
CONTESTO (schede RAG e dati stanza precisi, con i numeri già calcolati dal
backend — vedi calc.py).
"""
from __future__ import annotations

from typing import List, Optional

from . import calc
from .search import SearchHit

SYSTEM_PROMPT = (
    "Sei l'assistente virtuale di un hotel. Regole da rispettare SEMPRE:\n"
    "1. Rispondi SOLO con le informazioni presenti nel CONTESTO qui sotto.\n"
    "2. Se un'informazione non è nel contesto, dillo con onestà e proponi di far "
    "verificare alla reception. NON inventare nulla.\n"
    "3. Non calcolare né stimare numeri, prezzi, orari o conversioni: usa "
    "ESCLUSIVAMENTE i valori già presenti nel contesto (li calcola il sistema).\n"
    "4. Rispondi in italiano, in modo cortese e conciso.\n\n"
    "Esempio: se manca il prezzo di un servizio, NON inventarlo — di' che verrà "
    "confermato dalla reception."
)


def build_context(hits: List[SearchHit]) -> str:
    if not hits:
        return "(nessuna informazione pertinente trovata)"
    return "\n\n".join(f"- {h.title}: {h.content}" for h in hits)


def build_room_facts(room) -> str:
    """Fatti PRECISI di una stanza, con conversioni calcolate dal backend.

    `room` è un app.rooms.Room. Le conversioni (es. °C→K) sono già pronte, così
    l'IA non deve calcolarle.
    """
    lines = [
        f"Stanza {room.room_number} ({room.room_type}), piano {room.floor}, "
        f"{room.square_meters} m², fino a {room.max_guests} ospiti.",
        f"Letto: {room.bed_type}.",
    ]
    ac = room.air_conditioning or {}
    if ac.get("disponibile"):
        rng = ac.get("range_temperatura") or {}
        min_c, max_c = rng.get("min_celsius"), rng.get("max_celsius")
        if min_c is not None and max_c is not None:
            testo = f"Climatizzatore regolabile da {min_c}°C a {max_c}°C"
            if rng.get("supporta_kelvin"):
                min_k = calc.celsius_to_kelvin(min_c)
                max_k = calc.celsius_to_kelvin(max_c)
                testo += f" (equivalenti a {min_k} K – {max_k} K, calcolati dal sistema)"
            lines.append(testo + ".")
    if room.amenities:
        lines.append("Dotazioni: " + ", ".join(room.amenities) + ".")
    return "\n".join(lines)


def build_system_prompt(hits: List[SearchHit], room_facts: Optional[str] = None) -> str:
    parts = [SYSTEM_PROMPT, "\nCONTESTO:", build_context(hits)]
    if room_facts:
        parts.append("\nDATI STANZA (precisi):\n" + room_facts)
    return "\n".join(parts)
