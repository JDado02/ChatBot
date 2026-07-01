"""
Modelli di embedding — adapter intercambiabili.

- `OllamaEmbedder`: embedding REALI da un modello locale servito da Ollama
  (dev). In produzione si potrà sostituire con un embedder che parla con
  vLLM / un server dedicato, mantenendo la stessa interfaccia `Embedder`.
- `HashEmbedder`: embedder DETERMINISTICO e OFFLINE. NON ha alcuna qualità
  semantica — serve solo a far girare e testare la pipeline (plumbing) senza
  dover scaricare un modello. Utile in CI e quando manca la GPU.

Tutti gli embedder restituiscono vettori di dimensione `dim` (default 1024,
come bge-m3 / multilingual-e5), coerente con la colonna `vector(1024)`.
"""
from __future__ import annotations

import hashlib
import math
from typing import List, Optional, Protocol, Sequence


class Embedder(Protocol):
    dim: int

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        ...


class HashEmbedder:
    """Embedder deterministico offline (solo per test/plumbing)."""

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> List[float]:
        vec: List[float] = []
        counter = 0
        # Genera byte deterministici a partire dal testo finché non raggiunge dim.
        while len(vec) < self.dim:
            digest = hashlib.sha256(f"{counter}:{text}".encode("utf-8")).digest()
            for b in digest:
                vec.append((b / 255.0) * 2.0 - 1.0)  # mappa il byte in [-1, 1]
                if len(vec) >= self.dim:
                    break
            counter += 1
        # Normalizzazione L2: così il coseno si comporta bene e i vettori sono
        # confrontabili tra loro.
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


class OllamaEmbedder:
    """Embedder reale via Ollama (endpoint /api/embeddings)."""

    def __init__(
        self,
        url: str,
        model: str,
        dim: int = 1024,
        timeout: float = 60.0,
        transport=None,  # iniettabile nei test (httpx.MockTransport)
    ) -> None:
        self.url = url.rstrip("/")
        self.model = model
        self.dim = dim
        self.timeout = timeout
        self._transport = transport

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        import httpx  # import lazy: non serve a chi usa solo HashEmbedder

        out: List[List[float]] = []
        with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
            for text in texts:
                resp = client.post(
                    f"{self.url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                resp.raise_for_status()
                emb = resp.json().get("embedding")
                if emb is None:
                    raise ValueError("risposta Ollama priva del campo 'embedding'")
                if len(emb) != self.dim:
                    raise ValueError(
                        f"dimensione embedding attesa {self.dim}, ricevuta {len(emb)} "
                        f"(modello '{self.model}': controlla EMBEDDING_MODEL/EMBEDDING_DIM)"
                    )
                out.append([float(x) for x in emb])
        return out


def build_default_embedder(settings, fake: bool = False) -> Embedder:
    """Factory: HashEmbedder se `fake`, altrimenti OllamaEmbedder dai settings."""
    if fake:
        return HashEmbedder(settings.embedding_dim)
    return OllamaEmbedder(
        url=settings.ollama_url,
        model=settings.embedding_model,
        dim=settings.embedding_dim,
    )
