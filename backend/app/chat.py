"""
Orchestrazione della chat: RAG + memoria conversazione + LLM, con grounding.

Le regole di risposta e la costruzione del prompt (anti-allucinazione, dati
stanza con numeri già calcolati) stanno in `prompt.py`; qui c'è il flusso.

Flusso di `answer`:
  1. ricerca semantica sulla knowledge base del tenant (search_fn);
  2. salva il messaggio utente nella storia (store);
  3. costruisce il system prompt con regole + CONTESTO (+ eventuali dati stanza);
  4. chiama l'LLM con system + storia conversazione;
  5. salva la risposta e la ritorna con le fonti (titoli delle schede usate).

`answer` riceve `search_fn` (non il DB) così è testabile offline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

# Re-export per compatibilità: le regole/prompt vivono in prompt.py
from .prompt import SYSTEM_PROMPT, build_context, build_system_prompt  # noqa: F401
from .llm import LLMClient
from .search import SearchHit
from .sessions import SessionStore

# Funzione di ricerca: (tenant_id, query, k) -> list[SearchHit]
SearchFn = Callable[[str, str, int], List[SearchHit]]


@dataclass
class ChatReply:
    reply: str
    sources: List[str]


def answer(
    search_fn: SearchFn,
    store: SessionStore,
    llm: LLMClient,
    tenant_id: str,
    session_id: str,
    user_message: str,
    k: int = 4,
    room_facts: Optional[str] = None,
) -> ChatReply:
    hits = search_fn(tenant_id, user_message, k)
    store.append(tenant_id, session_id, "user", user_message)
    history = store.history(tenant_id, session_id)
    reply_text = llm.generate(build_system_prompt(hits, room_facts), history)
    store.append(tenant_id, session_id, "assistant", reply_text)
    return ChatReply(reply=reply_text, sources=[h.title for h in hits])
