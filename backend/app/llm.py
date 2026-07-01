"""
Adapter per il modello di linguaggio (LLM). Come per gli embedding, l'interfaccia
è intercambiabile:
- `OllamaLLM`: chat reale via Ollama (`/api/chat`) in dev; sostituibile con vLLM
  in produzione senza toccare il resto.
- `StubLLM`: risposta DETERMINISTICA e offline, per testare l'orchestrazione
  (RAG + storia + grounding) senza un modello. Non "ragiona".
"""
from __future__ import annotations

from typing import List, Protocol


class LLMClient(Protocol):
    def generate(self, system: str, messages: List[dict]) -> str: ...


class StubLLM:
    def generate(self, system: str, messages: List[dict]) -> str:
        last_user = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
        )
        return f"[stub] Rispondo solo dai dati forniti. Domanda ricevuta: {last_user!r}"


class OllamaLLM:
    def __init__(self, url: str, model: str, timeout: float = 120.0, transport=None) -> None:
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._transport = transport

    def generate(self, system: str, messages: List[dict]) -> str:
        import httpx

        payload = {
            "model": self.model,
            "stream": False,
            "messages": [{"role": "system", "content": system}] + list(messages),
        }
        with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
            resp = client.post(f"{self.url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        try:
            return data["message"]["content"]
        except (KeyError, TypeError):
            raise ValueError("risposta Ollama /api/chat inattesa (manca message.content)")
