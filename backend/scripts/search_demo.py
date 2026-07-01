"""
Demo da riga di comando della ricerca semantica.

Uso (dalla cartella backend/):
    python scripts/search_demo.py hotel_alpha "a che ora è la colazione?"
    python scripts/search_demo.py hotel_alpha "posso portare il cane?" --fake -k 3

Con --fake usa l'embedder offline: la pipeline gira ma i risultati NON sono
semanticamente sensati (serve solo a verificare il plumbing end-to-end).
Per risultati reali servono Ollama + embedding già generati con lo stesso modello.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.db import connect
from app.embeddings import build_default_embedder
from app.search import semantic_search


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Ricerca semantica sulla knowledge base.")
    parser.add_argument("tenant", help="tenant_id (es. hotel_alpha)")
    parser.add_argument("query", help="la domanda in linguaggio naturale")
    parser.add_argument("-k", type=int, default=5, help="numero di risultati (default 5)")
    parser.add_argument("--fake", action="store_true", help="embedder offline (solo plumbing)")
    args = parser.parse_args(argv)

    embedder = build_default_embedder(settings, fake=args.fake)
    with connect() as conn:
        hits = semantic_search(conn, args.tenant, args.query, embedder, k=args.k)

    if not hits:
        print("(nessun risultato: gli embedding sono stati generati?)")
        return 0
    for i, h in enumerate(hits, 1):
        print(f"{i}. [{h.category}] {h.title}  (score={h.score:.3f})")
        print(f"   {h.content[:120]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
