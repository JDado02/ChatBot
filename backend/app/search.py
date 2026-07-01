"""
Pipeline di embedding e ricerca semantica (RAG) sulla knowledge base.

Due funzioni principali:
- `store_embeddings`: genera e salva l'embedding delle schede che non ne hanno
  ancora (per un tenant), rispettando la RLS.
- `semantic_search`: data una domanda, ne calcola l'embedding e recupera le K
  schede più simili con pgvector (distanza coseno). La RLS garantisce che si
  vedano SOLO le schede del tenant corrente.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .db import tenant_transaction
from .embeddings import Embedder
from .vectors import to_pgvector


# Testo usato per l'embedding di una scheda: titolo + contenuto. Lo stesso
# criterio va mantenuto stabile nel tempo (se cambia, gli embedding vanno
# rigenerati).
def _doc_text(title: str, content: str) -> str:
    return f"{title}\n{content}"


def store_embeddings(conn, tenant_id: str, embedder: Embedder, batch: int = 100) -> int:
    """Popola knowledge_base.embedding per le schede del tenant ancora prive.

    Ritorna il numero di schede aggiornate.
    """
    updated = 0
    while True:
        with tenant_transaction(conn, tenant_id) as c:
            rows = c.execute(
                "SELECT id, title, content FROM knowledge_base "
                "WHERE embedding IS NULL ORDER BY id LIMIT %s",
                (batch,),
            ).fetchall()
            if not rows:
                break
            texts = [_doc_text(title, content) for (_id, title, content) in rows]
            vectors = embedder.embed(texts)
            for (rid, _t, _c), vec in zip(rows, vectors):
                c.execute(
                    "UPDATE knowledge_base SET embedding = %s::vector, updated_at = now() "
                    "WHERE id = %s",
                    (to_pgvector(vec), rid),
                )
            updated += len(rows)
    return updated


@dataclass
class SearchHit:
    id: int
    category: str
    title: str
    content: str
    metadata: Optional[dict]
    score: float  # similarità coseno in [-1, 1] (1 = identico)


def semantic_search(
    conn, tenant_id: str, query: str, embedder: Embedder, k: int = 5
) -> List[SearchHit]:
    """Ricerca semantica: ritorna le K schede più simili alla domanda.

    L'operatore `<=>` di pgvector è la distanza coseno; `1 - distanza` è la
    similarità. L'indice HNSW (vector_cosine_ops) rende la ricerca veloce.
    """
    qvec = to_pgvector(embedder.embed([query])[0])
    with tenant_transaction(conn, tenant_id) as c:
        rows = c.execute(
            """
            SELECT id, category, title, content, metadata,
                   1 - (embedding <=> %s::vector) AS score
            FROM knowledge_base
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (qvec, qvec, k),
        ).fetchall()

    return [
        SearchHit(
            id=r[0], category=r[1], title=r[2], content=r[3], metadata=r[4], score=float(r[5])
        )
        for r in rows
    ]
