"""
PocketFlow-based document import pipeline.

Pipeline stages (linear flow):
    FileReaderNode
        → MarkdownCleanerNode
        → HeaderChunkerNode
        → EmbedAndStoreNode

Each node reads/writes `shared`:
    Input keys (set by caller before running):
        path        str | Path  — file to import
        topic       str         — memory topic label
        realm       str         — memory realm (knowledge_base | institutional | sop)
        chunk_size  int         — max chars per chunk when no headers present
        source_tag  str | None  — optional URL or label stored in metadata
        agent_id    str         — agent identifier stored in metadata
        session_id  str         — session identifier stored in metadata
        store       MemoryStore — shared store instance

    Output keys (written by pipeline):
        chunks      list[str]   — chunks produced by HeaderChunkerNode
        stored_ids  list[str]   — IDs produced by EmbedAndStoreNode

Additional nodes can be inserted between any two existing nodes; just rewire
the successors after building the flow via `build_import_flow()`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pocketflow import Flow, Node

from memory.store import MemoryStore


# ---------------------------------------------------------------------------
# Stage 1 — File reader
# ---------------------------------------------------------------------------


class FileReaderNode(Node):
    """Read a file from disk into shared['raw_content']."""

    def prep(self, shared: dict[str, Any]) -> Path:
        return Path(shared["path"])

    def exec(self, prep_res: Path) -> str:
        try:
            return prep_res.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return prep_res.read_text(encoding="latin-1")

    def post(self, shared: dict[str, Any], prep_res: Any, exec_res: str) -> str:
        shared["raw_content"] = exec_res
        return "default"


# ---------------------------------------------------------------------------
# Stage 2 — Markdown cleaner
# ---------------------------------------------------------------------------


def clean_markdown(md: str) -> str:
    """Strip noise from raw markdown (empty lines, cookie/nav junk)."""
    lines = md.splitlines()
    cleaned: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        if "cookie" in line.lower():
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


class MarkdownCleanerNode(Node):
    """Clean raw content and write to shared['clean_content']."""

    def prep(self, shared: dict[str, Any]) -> str:
        return shared.get("raw_content", "")

    def exec(self, prep_res: str) -> str:
        return clean_markdown(prep_res)

    def post(self, shared: dict[str, Any], prep_res: Any, exec_res: str) -> str:
        shared["clean_content"] = exec_res
        return "default"


# ---------------------------------------------------------------------------
# Stage 3 — Header-based chunker
# ---------------------------------------------------------------------------

_HEADER_PATTERN = re.compile(r"\n(?=## )")
_DEFAULT_CHUNK_SIZE = 4000  # chars


def split_by_headers(text: str) -> list[str]:
    """Split on `## ` level-2 headers, keeping the header prefix on each part."""
    parts = _HEADER_PATTERN.split(text)
    return [p.strip() for p in parts if p.strip()]


def fixed_size_chunks(text: str, size: int) -> list[str]:
    """Fall back to fixed-size character chunks when no headers are found."""
    return [text[i : i + size].strip() for i in range(0, len(text), size) if text[i : i + size].strip()]


class HeaderChunkerNode(Node):
    """Split cleaned content into chunks, write to shared['chunks']."""

    def prep(self, shared: dict[str, Any]) -> tuple[str, int]:
        return shared.get("clean_content", ""), shared.get("chunk_size", _DEFAULT_CHUNK_SIZE)

    def exec(self, prep_res: tuple[str, int]) -> list[str]:
        text, chunk_size = prep_res
        if not text:
            return []
        chunks = split_by_headers(text)
        if len(chunks) <= 1:
            # No meaningful header splits — use fixed-size
            chunks = fixed_size_chunks(text, chunk_size)
        return chunks or [text.strip()]

    def post(self, shared: dict[str, Any], prep_res: Any, exec_res: list[str]) -> str:
        shared["chunks"] = exec_res
        return "default"


# ---------------------------------------------------------------------------
# Stage 4 — Embed & store
# ---------------------------------------------------------------------------


class EmbedAndStoreNode(Node):
    """Store all chunks into MemoryStore, write IDs to shared['stored_ids']."""

    def prep(self, shared: dict[str, Any]) -> dict[str, Any]:
        return {
            "chunks": shared.get("chunks", []),
            "store": shared["store"],
            "topic": shared["topic"],
            "realm": shared["realm"],
            "agent_id": shared.get("agent_id", "memory_cli"),
            "session_id": shared.get("session_id", "import"),
            "source_tag": shared.get("source_tag"),
            "path": str(shared.get("path", "")),
        }

    def exec(self, prep_res: dict[str, Any]) -> list[str]:
        store: MemoryStore = prep_res["store"]
        stored_ids: list[str] = []
        for i, chunk in enumerate(prep_res["chunks"]):
            if not chunk:
                continue
            keywords: list[str] = []
            if prep_res["source_tag"]:
                keywords.append(prep_res["source_tag"])
            if prep_res["path"]:
                keywords.append(f"file:{prep_res['path']}")
            keywords.append(f"chunk:{i}")
            doc_id = store.store(
                content=chunk,
                topic=prep_res["topic"],
                realm=prep_res["realm"],
                agent_id=prep_res["agent_id"],
                session_id=prep_res["session_id"],
                keywords=keywords,
            )
            stored_ids.append(doc_id)
        return stored_ids

    def post(self, shared: dict[str, Any], prep_res: Any, exec_res: list[str]) -> str:
        shared["stored_ids"] = exec_res
        return "default"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_import_flow() -> Flow:
    """
    Construct and wire the default linear import pipeline.

    Returns a ready-to-run Flow.  Callers can insert custom nodes after the
    fact by replacing successor links.

    Example — adding a custom HTML-stripping stage before the cleaner::

        flow = build_import_flow()
        html_node = HTMLStripperNode()
        # Insert before cleaner: reader -> html_node -> cleaner
        reader = flow.start_node
        cleaner = reader.successors["default"]
        reader.successors["default"] = html_node
        html_node.next(cleaner)
    """
    reader = FileReaderNode()
    cleaner = MarkdownCleanerNode()
    chunker = HeaderChunkerNode()
    storer = EmbedAndStoreNode()

    reader.next(cleaner)
    cleaner.next(chunker)
    chunker.next(storer)

    return Flow(start=reader)


def import_file(
    path: str | Path,
    topic: str,
    realm: str,
    store: MemoryStore,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    source_tag: str | None = None,
    agent_id: str = "memory_cli",
    session_id: str = "import",
) -> list[str]:
    """
    Convenience wrapper: run the import pipeline on a single file.

    Returns the list of stored document IDs.
    """
    flow = build_import_flow()
    shared: dict[str, Any] = {
        "path": Path(path),
        "topic": topic,
        "realm": realm,
        "store": store,
        "chunk_size": chunk_size,
        "source_tag": source_tag,
        "agent_id": agent_id,
        "session_id": session_id,
    }
    flow.run(shared)
    return shared.get("stored_ids", [])
