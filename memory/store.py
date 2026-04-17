"""ChromaDB-backed memory store using Bedrock Titan embeddings."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import chromadb
from chromadb import EmbeddingFunction, Embeddings

_REALMS = ("knowledge_base", "institutional", "sop", "agent_facts")
_DEFAULT_N_RESULTS = 10


class BedrockEmbeddingFunction(EmbeddingFunction):
    """Bedrock Titan Embeddings v2 — keeps everything on AWS."""

    def __init__(self, model_id: str = "amazon.titan-embed-text-v2:0") -> None:
        self.model_id = model_id
        self._client = boto3.client("bedrock-runtime")

    def __call__(self, input: list[str]) -> Embeddings:
        embeddings: Embeddings = []
        for text in input:
            body = json.dumps({"inputText": text[:8000]})  # Titan v2 max 8k chars
            response = self._client.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            result = json.loads(response["body"].read())
            embeddings.append(result["embedding"])
        return embeddings


class MemoryStore:
    """
    Shared in-process ChromaDB store.

    Three collections (realms): knowledge_base, institutional, sop.
    All agents share the same collections — cross-agent memory is built-in.

    Document metadata schema:
        realm, topic, keywords (comma-separated), agent_id, session_id, timestamp
    """

    def __init__(self, db_path: str | None = None) -> None:
        from engine.paths import MEMORY_DB_DIR
        resolved_path = Path(db_path) if db_path is not None else MEMORY_DB_DIR
        self._ef = BedrockEmbeddingFunction()
        self._client = chromadb.PersistentClient(path=str(resolved_path.resolve()))
        self._collections: dict[str, chromadb.Collection] = {
            realm: self._client.get_or_create_collection(
                name=realm,
                embedding_function=self._ef,
                metadata={"hnsw:space": "cosine"},
            )
            for realm in _REALMS
        }
        # Topic centroid collection for two-stage retrieval
        self._centroids = self._client.get_or_create_collection(
            name="topic-centroids",
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )

    def store(
        self,
        content: str,
        topic: str,
        realm: str,
        agent_id: str,
        session_id: str,
        keywords: list[str] | None = None,
    ) -> str:
        """Store a document and update topic centroid. Returns the new document ID."""
        if realm not in _REALMS:
            raise ValueError(f"Unknown realm '{realm}'. Must be one of: {_REALMS}")

        doc_id = uuid.uuid4().hex
        metadata: dict[str, Any] = {
            "realm": realm,
            "topic": topic,
            "keywords": ",".join(keywords or []),
            "agent_id": agent_id,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._collections[realm].add(
            documents=[content],
            metadatas=[metadata],
            ids=[doc_id],
        )
        self._update_centroid(topic, realm, content)
        return doc_id

    def search(
        self,
        query: str,
        realm: str | None = None,
        topic: str | None = None,
        n_results: int = _DEFAULT_N_RESULTS,
    ) -> list[dict[str, Any]]:
        """
        Two-stage semantic search.

        Stage 1: If no topic given, find the top matching topics via centroid search.
        Stage 2: Full semantic search within those topics.

        Returns list of {id, content, metadata, distance} dicts sorted by relevance.
        """
        target_realms = [realm] if realm else list(_REALMS)
        if topic:
            target_topics: list[str] = [topic]
        else:
            try:
                target_topics = self._find_relevant_topics(query, top_k=5)
            except Exception:
                target_topics = []  # fall back to unfiltered search across all realms

        results: list[dict[str, Any]] = []
        for r in target_realms:
            col = self._collections[r]
            if col.count() == 0:
                continue
            where: dict[str, Any] | None = None
            if target_topics:
                where = {"topic": {"$in": target_topics}}
            try:
                raw = col.query(
                    query_texts=[query],
                    n_results=min(n_results, col.count()),
                    where=where,
                )
            except Exception:
                # Fallback: search without topic filter
                try:
                    raw = col.query(
                        query_texts=[query],
                        n_results=min(n_results, col.count()),
                    )
                except Exception:
                    continue

            for i, doc_id in enumerate(raw["ids"][0]):
                results.append(
                    {
                        "id": doc_id,
                        "content": raw["documents"][0][i],
                        "metadata": raw["metadatas"][0][i],
                        "distance": raw["distances"][0][i],
                    }
                )

        results.sort(key=lambda x: x["distance"])
        return results[:n_results]

    def update(self, doc_id: str, content: str, realm: str) -> bool:
        """Update the content of an existing document. Returns True if found."""
        if realm not in _REALMS:
            raise ValueError(f"Unknown realm '{realm}'.")
        col = self._collections[realm]
        existing = col.get(ids=[doc_id])
        if not existing["ids"]:
            return False
        col.update(ids=[doc_id], documents=[content])
        return True

    def delete(self, doc_id: str, realm: str) -> bool:
        """Delete a document by ID. Returns True if found and deleted."""
        if realm not in _REALMS:
            raise ValueError(f"Unknown realm '{realm}'.")
        col = self._collections[realm]
        existing = col.get(ids=[doc_id])
        if not existing["ids"]:
            return False
        col.delete(ids=[doc_id])
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_centroid(self, topic: str, realm: str, new_text: str) -> None:
        """Upsert a representative document for the topic in the centroid collection."""
        centroid_id = f"{realm}__{topic}"
        existing = self._centroids.get(ids=[centroid_id])
        if existing["ids"]:
            # Append a snippet so the centroid embedding drifts toward all docs
            old_doc: str = existing["documents"][0]
            combined = f"{old_doc} {new_text}"[:2000]
            self._centroids.update(
                ids=[centroid_id],
                documents=[combined],
                metadatas=[{"realm": realm, "topic": topic}],
            )
        else:
            self._centroids.add(
                ids=[centroid_id],
                documents=[new_text[:2000]],
                metadatas=[{"realm": realm, "topic": topic}],
            )

    def _find_relevant_topics(self, query: str, top_k: int = 5) -> list[str]:
        """Return the top-K most relevant topic names for a query via centroid search."""
        count = self._centroids.count()
        if count == 0:
            return []
        raw = self._centroids.query(
            query_texts=[query],
            n_results=min(top_k, count),
        )
        return [meta["topic"] for meta in raw["metadatas"][0]]
