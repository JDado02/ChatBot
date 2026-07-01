"""
Popola knowledge_base.embedding per uno o più tenant.

Uso (dalla cartella backend/):
    python scripts/generate_embeddings.py hotel_alpha hotel_beta
    python scripts/generate_embeddings.py hotel_alpha --fake   # offline, senza modello

Prerequisiti: container Postgres su (docker compose up -d) e, senza --fake,
Ollama in esecuzione con il modello di embedding scaricato
(es. `ollama pull bge-m3`).
"""
from __future__ import annotations

import argparse
import os
import sys

# Permette `from app...` quando lo script è lanciato direttamente.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.db import connect
from app.embeddings import build_default_embedder
from app.search import store_embeddings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Genera gli embedding della knowledge base.")
    parser.add_argument("tenants", nargs="+", help="uno o più tenant_id (es. hotel_alpha)")
    parser.add_argument(
        "--fake", action="store_true",
        help="usa l'embedder deterministico offline (nessun modello richiesto)",
    )
    args = parser.parse_args(argv)

    embedder = build_default_embedder(settings, fake=args.fake)
    mode = "HashEmbedder (offline)" if args.fake else f"Ollama '{settings.embedding_model}'"
    print(f"[embeddings] modello: {mode}, dim={settings.embedding_dim}")

    with connect() as conn:
        for tenant in args.tenants:
            n = store_embeddings(conn, tenant, embedder)
            print(f"[embeddings] {tenant}: {n} schede aggiornate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
