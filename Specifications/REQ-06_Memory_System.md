# REQ-06: Memory System

## Overview
A searchable database that stores knowledge agents may need across sessions. Memory has scopes (permanent, shared, temporary), is structured with keywords and context, and is searchable by question or keyword.

## Source
- [00_The Council.md](../00_The%20Council.md) → Memory

## Phase
Phase 1 — MVP (Critical)

## Functional Requirements

- **FR-06.01**: Memory entries stored in S3 as JSON objects under `memory/{agent_id}/` with fields: ID, content, keywords, embedding_vector, related_info, scope, agent_id, created_at, updated_at, source_session_id.
- **FR-06.02**: Three memory scopes: **permanent** (survives agent lifetime), **shared** (accessible to all agents), **temporary** (session-scoped, auto-cleaned).
- **FR-06.03**: Memory is searchable by natural language question (semantic search via embeddings stored in S3) or by keyword matching.
- **FR-06.04**: Each memory entry is structured: the information itself, keywords for retrieval, and related context explaining why the memory exists.
- **FR-06.05**: Memory can store: events/conversations, facts, numbers, commonly used data, short-term goals, and any other agent-useful information.
- **FR-06.06**: Memory **cannot** store: passwords, secrets, or large data (large data must be stored as files in S3 and referenced).
- **FR-06.07**: Memory validation rejects entries containing secret-like patterns (API keys, passwords, tokens).
- **FR-06.08**: Memory entries can be created, read, updated, and deleted. Deletion of permanent memories requires confirmation.
- **FR-06.09**: Embeddings for semantic search stored alongside entries in S3 JSON (vector field in each entry). Search uses cosine similarity.
- **FR-06.10**: Memory retrieval returns ranked results with relevance scores.

## Non-Functional Requirements

- **NFR-06.01**: Keyword search returns in under 200ms.
- **NFR-06.02**: Semantic search returns in under 2 seconds (including embedding generation).
- **NFR-06.03**: Memory system handles up to 100,000 entries per agent without degradation.

## Acceptance Criteria

- **AC-06.01**: An agent stores a memory entry with content, keywords, and context. The entry is retrievable.
- **AC-06.02**: Keyword search for a stored term returns the correct entry.
- **AC-06.03**: Natural language question retrieves a semantically relevant entry (e.g., "What was the result of the marketing meeting?" finds a meeting summary).
- **AC-06.04**: Permanent memory persists across sessions. Temporary memory is gone after session ends.
- **AC-06.05**: Shared memory created by Agent A is accessible to Agent B.
- **AC-06.06**: Attempting to store a string matching a secret pattern (e.g., `AKIA...`, `sk-...`) is rejected.
- **AC-06.07**: Large data storage attempt is rejected with guidance to use S3 file storage instead.
- **AC-06.08**: Search results are ranked by relevance and include scores.

## QA Checklist

- [ ] **Unit Tests**: CRUD operations, scope enforcement, secret detection, keyword search, embedding generation.
- [ ] **Integration Tests**: Agent stores memory in one session, retrieves it in another. Shared memory across agents.
- [ ] **Human Walkthrough**: Create memories via agent, search by keyword and by question, verify results and ranking.
- [ ] **Constitution: Security (VI)**: Secret detection prevents credential storage. No cleartext secrets in S3.
- [ ] **Constitution: Observability (V)**: Memory operations logged.
- [ ] **Constitution: Serverless-First (I)**: S3 for storage, Lambda for compute. No persistent search servers.
- [ ] **Constitution: Simplicity (VII)**: Start with keyword + cosine similarity over S3 embeddings.

## Dependencies

- **Depends on**: REQ-01 (S3), REQ-05 (Workflow Engine creates memories)
- **Blocks**: REQ-12 (Long-term agents need memory)
