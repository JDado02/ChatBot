"""
Memoria delle conversazioni. Ogni conversazione è isolata con chiave
`tenant_id:session_id` (due utenti diversi = due chiavi diverse) e ha un TTL,
così scade da sola (privacy + niente accumulo di dati personali).

`InMemorySessionStore` per test/single-process; `RedisSessionStore` per il
backend stateless in produzione.
"""
from __future__ import annotations

import json
from typing import Dict, List, Protocol


def session_key(tenant_id: str, session_id: str) -> str:
    return f"{tenant_id}:{session_id}"


class SessionStore(Protocol):
    def append(self, tenant_id: str, session_id: str, role: str, content: str) -> None: ...
    def history(self, tenant_id: str, session_id: str) -> List[dict]: ...


class InMemorySessionStore:
    def __init__(self, max_messages: int = 50) -> None:
        self._data: Dict[str, List[dict]] = {}
        self.max_messages = max_messages

    def append(self, tenant_id: str, session_id: str, role: str, content: str) -> None:
        msgs = self._data.setdefault(session_key(tenant_id, session_id), [])
        msgs.append({"role": role, "content": content})
        # mantieni solo gli ultimi max_messages
        if len(msgs) > self.max_messages:
            del msgs[: -self.max_messages]

    def history(self, tenant_id: str, session_id: str) -> List[dict]:
        return list(self._data.get(session_key(tenant_id, session_id), []))


class RedisSessionStore:
    """Storia su lista Redis (JSON per messaggio), con trim + TTL."""

    def __init__(self, redis, ttl_seconds: int = 3600, max_messages: int = 50) -> None:
        self.redis = redis
        self.ttl = ttl_seconds
        self.max_messages = max_messages

    def append(self, tenant_id: str, session_id: str, role: str, content: str) -> None:
        key = session_key(tenant_id, session_id)
        self.redis.rpush(key, json.dumps({"role": role, "content": content}))
        self.redis.ltrim(key, -self.max_messages, -1)
        self.redis.expire(key, self.ttl)

    def history(self, tenant_id: str, session_id: str) -> List[dict]:
        key = session_key(tenant_id, session_id)
        return [json.loads(x) for x in self.redis.lrange(key, 0, -1)]
