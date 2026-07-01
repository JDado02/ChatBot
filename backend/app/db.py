"""
Accesso al database con isolamento multi-tenant (RLS).

Il pezzo CRITICO è `tenant_transaction`: prima di ogni query imposta
l'identità del tenant con
    SELECT set_config('app.current_tenant', <id>, true)
Il terzo argomento `true` significa "local": l'impostazione vale SOLO per la
transazione corrente e NON resta attaccata alla connessione. Fondamentale con
il connection pooling: senza, una richiesta di un hotel potrebbe ereditare il
contesto di un altro (fuga di dati).

`set_config(..., true)` è l'equivalente parametrizzabile di
`SET LOCAL app.current_tenant = ...` (SET LOCAL non accetta bind param per il
valore, quindi useremmo string-interpolation → rischio SQL injection).

Nota: qui si usa psycopg in modalità SINCRONA perché la pipeline di embedding
è un job batch. Il percorso richiesta di FastAPI (Passo 6) userà psycopg
ASYNC con lo STESSO identico pattern set_config.
"""
from __future__ import annotations

import contextlib
from typing import Iterator

import psycopg

from .config import settings


def connect() -> "psycopg.Connection":
    """Apre una connessione come ruolo app_user (soggetto a RLS)."""
    return psycopg.connect(settings.dsn)


@contextlib.contextmanager
def tenant_transaction(conn: "psycopg.Connection", tenant_id: str) -> Iterator["psycopg.Connection"]:
    """Transazione con l'identità del tenant impostata per la RLS.

    Uso:
        with connect() as conn:
            with tenant_transaction(conn, "hotel_alpha") as c:
                c.execute("SELECT ... FROM knowledge_base ...")
    """
    if not tenant_id:
        # Fail-safe esplicito: senza tenant la RLS non mostrerebbe nulla; meglio
        # bloccare subito con un errore chiaro che eseguire query "cieche".
        raise ValueError("tenant_id obbligatorio per operare sotto RLS")

    with conn.transaction():
        conn.execute("SELECT set_config('app.current_tenant', %s, true)", (tenant_id,))
        yield conn
