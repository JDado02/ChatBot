"""
Utility per i vettori pgvector — funzioni PURE, senza dipendenze da DB o rete,
quindi interamente testabili offline.
"""
from __future__ import annotations

import math
from typing import Sequence


def to_pgvector(vec: Sequence[float]) -> str:
    """Converte una lista di float nel literal testuale di pgvector: '[x,y,z]'.

    Va passato come parametro e castato lato SQL con `%s::vector`. Evita di
    dover dipendere dal pacchetto `pgvector` a livello di import.
    """
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def parse_pgvector(s: str) -> list[float]:
    """Inverso di to_pgvector: '[x,y,z]' -> [x, y, z]."""
    s = s.strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    s = s.strip()
    if not s:
        return []
    return [float(p) for p in s.split(",")]


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Similarità coseno in [-1, 1]. Usata nei test per validare il ranking
    senza dover interrogare pgvector."""
    if len(a) != len(b):
        raise ValueError(f"dimensioni diverse: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
