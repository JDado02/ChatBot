"""
Token di sessione a vita breve, firmati con HMAC-SHA256.

Quando il widget si carica da un dominio autorizzato, il backend emette un
token temporaneo legato al `session_id` (e al tenant). È quel token, non l'API
key, a viaggiare nelle richieste successive: anche se intercettato, scade in
pochi minuti.

Implementazione senza dipendenze (stdlib): formato `<payload_b64>.<sig_b64>`,
con clock iniettabile (`now_ts`) per rendere i test deterministici.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Optional


class TokenError(Exception):
    pass


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def issue_token(
    payload: dict, secret: str, ttl_seconds: int = 300, now_ts: Optional[float] = None
) -> str:
    """Emette un token firmato con `iat`/`exp` aggiunti automaticamente."""
    now = int(now_ts if now_ts is not None else time.time())
    body = dict(payload)
    body["iat"] = now
    body["exp"] = now + ttl_seconds
    part = _b64url_encode(
        json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    sig = hmac.new(secret.encode("utf-8"), part.encode("ascii"), hashlib.sha256).digest()
    return f"{part}.{_b64url_encode(sig)}"


def verify_token(token: str, secret: str, now_ts: Optional[float] = None) -> dict:
    """Verifica firma e scadenza; ritorna il payload o solleva TokenError."""
    try:
        part, sig_b64 = token.split(".", 1)
    except ValueError:
        raise TokenError("formato token non valido")

    expected = hmac.new(secret.encode("utf-8"), part.encode("ascii"), hashlib.sha256).digest()
    try:
        got = _b64url_decode(sig_b64)
    except Exception:
        raise TokenError("firma non decodificabile")
    # Confronto a tempo costante: evita timing attack sulla firma.
    if not hmac.compare_digest(expected, got):
        raise TokenError("firma non valida")

    try:
        payload = json.loads(_b64url_decode(part))
    except Exception:
        raise TokenError("payload non valido")

    now = int(now_ts if now_ts is not None else time.time())
    if "exp" in payload and now >= payload["exp"]:
        raise TokenError("token scaduto")
    return payload
