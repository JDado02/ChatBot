"""
Rate limiting a finestra fissa: massimo `limit` richieste per `window_seconds`
per chiave (es. api_key o IP). Serve a bloccare lo scraping della knowledge base
e l'abuso della GPU (la voce di costo più cara).

Due implementazioni con la stessa interfaccia `allow(key) -> bool`:
- `InMemoryRateLimiter`: per single-process / test (clock iniettabile).
- `RedisRateLimiter`: per produzione (backend stateless su più processi).
"""
from __future__ import annotations

import time
from typing import Callable, Dict, Optional, Tuple


class InMemoryRateLimiter:
    def __init__(
        self, limit: int, window_seconds: int, now: Optional[Callable[[], float]] = None
    ) -> None:
        self.limit = limit
        self.window = window_seconds
        self._now = now or time.time
        self._state: Dict[str, Tuple[int, float]] = {}  # key -> (count, window_start)

    def allow(self, key: str) -> bool:
        now = self._now()
        count, start = self._state.get(key, (0, now))
        if now - start >= self.window:
            count, start = 0, now  # finestra scaduta: riparte
        count += 1
        self._state[key] = (count, start)
        return count <= self.limit

    def reset(self, key: str) -> None:
        self._state.pop(key, None)


class RedisRateLimiter:
    """INCR sulla chiave; EXPIRE impostato solo alla prima richiesta della
    finestra. `redis` è un client con i metodi `incr` ed `expire`."""

    def __init__(self, redis, limit: int, window_seconds: int, prefix: str = "rl:") -> None:
        self.redis = redis
        self.limit = limit
        self.window = window_seconds
        self.prefix = prefix

    def allow(self, key: str) -> bool:
        rkey = self.prefix + key
        count = int(self.redis.incr(rkey))
        if count == 1:
            self.redis.expire(rkey, self.window)
        return count <= self.limit
