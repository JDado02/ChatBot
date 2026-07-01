"""
Lookup del tenant dall'API key ricevuta dal widget.

La tabella `tenants` NON è sotto la RLS per-tenant (è la tabella di lookup che
determina quale tenant siamo), quindi qui NON si imposta app.current_tenant.
Dopo aver identificato il tenant, ogni accesso ai DATI di quel tenant deve
comunque passare da `db.tenant_transaction`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Tenant:
    tenant_id: str
    name: str
    allowed_domains: List[str]
    active: bool


def get_tenant_by_api_key(conn, api_key: str) -> Optional[Tenant]:
    """Ritorna il Tenant attivo con quell'API key, o None se assente/disattivo."""
    if not api_key:
        return None
    row = conn.execute(
        "SELECT tenant_id, name, allowed_domains, active "
        "FROM tenants WHERE api_key = %s AND active = true",
        (api_key,),
    ).fetchone()
    if not row:
        return None
    return Tenant(
        tenant_id=row[0], name=row[1], allowed_domains=list(row[2] or []), active=row[3]
    )
