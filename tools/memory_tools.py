"""Memory tools — ChromaDB-backed via Bedrock Titan embeddings."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.store import MemoryStore
from tools import ToolContext, tool

_store: MemoryStore | None = None


def _get_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store


@tool
def store_memory(content: str, topic: str, realm: str, context: ToolContext) -> str:
    """Store a piece of information in shared memory with a topic and realm tag. Realms: knowledge_base | institutional | sop"""
    doc_id = _get_store().store(
        content=content,
        topic=topic,
        realm=realm,
        agent_id=context.agent_id,
        session_id=context.session_id,
    )
    return f"Stored memory id={doc_id} topic={topic} realm={realm}"


@tool
def search_memory(query: str, context: ToolContext) -> str:
    """Search shared memory using a natural language query. Returns ranked results from all agents and realms."""
    results = _get_store().search(query=query, n_results=5)
    if not results:
        return "No relevant memories found."
    lines = []
    for r in results:
        meta = r["metadata"]
        lines.append(
            f"[{meta.get('realm','?')}] {meta.get('topic','?')} "
            f"(by {meta.get('agent_id','?')} on {meta.get('timestamp','?')[:10]})\n"
            f"{r['content'][:500]}"
        )
    return "\n\n---\n\n".join(lines)


@tool
def update_memory(memory_id: str, content: str, realm: str, context: ToolContext) -> str:
    """Update an existing memory entry by ID."""
    found = _get_store().update(doc_id=memory_id, content=content, realm=realm)
    return f"Updated id={memory_id}" if found else f"Memory id={memory_id} not found in realm={realm}"


@tool
def delete_memory(memory_id: str, realm: str, context: ToolContext) -> str:
    """Delete a memory entry by ID."""
    found = _get_store().delete(doc_id=memory_id, realm=realm)
    return f"Deleted id={memory_id}" if found else f"Memory id={memory_id} not found in realm={realm}"

