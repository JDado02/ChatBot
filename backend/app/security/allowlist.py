"""
Allowlist dei domini: si accetta una richiesta del widget solo se l'header
`Origin` (o, in fallback, `Referer`) proviene da un dominio autorizzato per quel
tenant. Una API key copiata su un altro sito viene così rifiutata.

Politica: match ESATTO dell'host (case-insensitive), niente wildcard di
sottodominio, e **fail-closed** (in caso di dubbio si nega).
"""
from __future__ import annotations

from typing import Iterable, Optional
from urllib.parse import urlparse


def extract_host(url: Optional[str]) -> Optional[str]:
    """Estrae l'host da un Origin/Referer/dominio. Ritorna None se assente."""
    if not url:
        return None
    # Origin è "schema://host[:porta]"; un dominio nudo ("localhost") non ha //.
    parsed = urlparse(url if "//" in url else "//" + url.strip())
    return parsed.hostname.lower() if parsed.hostname else None


def normalize_domains(domains: Iterable[str]) -> set:
    """Normalizza i domini autorizzati a soli host minuscoli."""
    out = set()
    for d in domains or []:
        host = extract_host(d)
        if host:
            out.add(host)
    return out


def is_origin_allowed(
    origin: Optional[str], referer: Optional[str], allowed_domains: Iterable[str]
) -> bool:
    """True se l'host di Origin (preferito) o Referer è tra i domini autorizzati."""
    allowed = normalize_domains(allowed_domains)
    if not allowed:
        return False  # nessun dominio configurato => nega (fail-closed)
    host = extract_host(origin) or extract_host(referer)
    if not host:
        return False  # senza Origin/Referer non autorizziamo
    return host in allowed
