"""
Orchestrazione della chat: RAG + memoria conversazione + LLM, con grounding.

Flusso di `answer`:
  1. ricerca semantica sulla knowledge base del tenant (search_fn);
  2. salva il messaggio utente nella storia (store);
  3. costruisce il system prompt con le regole anti-allucinazione + il CONTESTO
     recuperato;
  4. chiama l'LLM con system + storia conversazione;
  5. salva la risposta e la ritorna con le fonti (titoli delle schede usate).

Il system prompt "definitivo" (regole complete + dati/calcoli deterministici:
prezzi, orari, conversioni) è materia del Passo 7; qui c'è una base solida di
grounding. `answer` riceve `search_fn` (non il DB) così è testabile offline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from .llm import LLMClient
from .search import SearchHit
from .sessions import SessionStore

SYSTEM_PROMPT = (
    "Sei l'assistente virtuale di un hotel. Rispondi SOLO usando le informazioni "
    "presenti nel CONTESTO qui sotto. Se l'informazione non è nel contesto, dillo "
    "chiaramente e proponi di far verificare alla reception: NON inventare nulla, "
    "in particolare numeri, prezzi e orari. Rispondi in italiano, in modo cortese "
    "e conciso."
)

# Funzione di ricerca: (tenant_id, query, k) -> list[SearchHit]
SearchFn = Callable[[str, str, int], List[SearchHit]]


def build_context(hits: List[SearchHit]) -> str:
    if not hits:
        return "(nessuna informazione pertinente trovata)"
    return "\n\n".join(f"- {h.title}: {h.content}" for h in hits)


def build_system_prompt(hits: List[SearchHit]) -> str:
    return f"{SYSTEM_PROMPT}\n\nCONTESTO:\n{build_context(hits)}"


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
) -> ChatReply:
    hits = search_fn(tenant_id, user_message, k)
    store.append(tenant_id, session_id, "user", user_message)
    history = store.history(tenant_id, session_id)
    reply_text = llm.generate(build_system_prompt(hits), history)
    store.append(tenant_id, session_id, "assistant", reply_text)
    return ChatReply(reply=reply_text, sources=[h.title for h in hits])
