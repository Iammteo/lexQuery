"""
Conversation memory service.

Stores query/answer pairs per session in memory (Redis in production).
A session is scoped to a user + workspace combination.

Memory window: last 5 turns to keep context relevant without bloat.
"""
import uuid
import logging
from typing import List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# In-memory store keyed by session_id
# Format: { session_id: [Turn, ...] }
_sessions: dict[str, list] = {}

MAX_TURNS = 5


@dataclass
class Turn:
    query: str
    answer: str


def get_session_id(user_id: uuid.UUID, workspace_id: uuid.UUID) -> str:
    """Generate a session key from user + workspace."""
    return f"{user_id}:{workspace_id}"


def get_history(session_id: str) -> List[Turn]:
    """Return the last MAX_TURNS turns for a session."""
    return _sessions.get(session_id, [])[-MAX_TURNS:]


def add_turn(session_id: str, query: str, answer: str) -> None:
    """Add a query/answer pair to the session history."""
    if session_id not in _sessions:
        _sessions[session_id] = []
    _sessions[session_id].append(Turn(query=query, answer=answer))
    # Trim to avoid unbounded growth
    _sessions[session_id] = _sessions[session_id][-MAX_TURNS * 2:]
    logger.debug(f"[memory] session={session_id} turns={len(_sessions[session_id])}")


def clear_session(session_id: str) -> None:
    """Clear all history for a session."""
    _sessions.pop(session_id, None)


def format_history_for_prompt(turns: List[Turn]) -> str:
    """Format conversation history into a string for the LLM prompt."""
    if not turns:
        return ""
    lines = []
    for t in turns:
        lines.append(f"User: {t.query}")
        # Truncate long answers to keep prompt size manageable
        answer_preview = t.answer[:400] + "..." if len(t.answer) > 400 else t.answer
        lines.append(f"Assistant: {answer_preview}")
    return "\n".join(lines)


def rewrite_query_with_context(query: str, history: List[Turn]) -> str:
    """
    Rewrite a follow-up question into a self-contained query.

    E.g. "Does that apply to both parties?" with context about a
    termination clause → "Does the 30-day termination notice period
    apply to both parties?"

    This is done by the LLM in the answer_service — this function
    just checks if rewriting is needed (i.e. the query contains
    pronouns or references that require context).
    """
    if not history:
        return query

    # Heuristic: if query contains referential terms, it needs rewriting
    referential = ["that", "this", "it", "they", "them", "those", "these",
                   "the clause", "the provision", "the agreement", "the same",
                   "above", "mentioned", "previously", "earlier"]
    query_lower = query.lower()
    needs_rewrite = any(ref in query_lower for ref in referential)
    return query if not needs_rewrite else f"__NEEDS_REWRITE__:{query}"
