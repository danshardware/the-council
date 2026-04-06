# Task: Memory CRUD and Storage

## Parent
- **Requirement**: REQ-06 Memory System
- **Story**: S01 Memory Storage

## Description
Implement memory entry creation, reading, updating, and deletion in S3. Entries stored as JSON objects under `memory/` prefix. Include scope management, validation (no secrets), and structured entry format. Each entry also generates an embedding vector stored alongside for search.

## Acceptance Criteria
- [ ] **AC-01**: `MemoryStore` class implements create, read, update, delete operations against S3.
- [ ] **AC-02**: Entries stored at `memory/{agent_id}/{memory_id}.json` with fields: id, content, keywords[], embedding_vector, related_info, scope, agent_id, created_at, updated_at, source_session_id.
- [ ] **AC-03**: Three scopes enforced: permanent (no auto-delete), shared (cross-agent, stored under `memory/shared/`), temporary (deleted after session).
- [ ] **AC-04**: Secret pattern detection rejects entries containing API keys, tokens, or passwords.
- [ ] **AC-05**: Deletion of permanent memories requires a confirmation flag.
- [ ] **AC-06**: Temporary memories are cleaned up when their session ends.
- [ ] **AC-07**: On create/update, an embedding vector is generated via Bedrock Titan Embeddings and stored in the entry.

## QA Checklist
- [ ] pytest tests: CRUD operations, scope enforcement, secret detection patterns, cleanup, embedding generation.
- [ ] **Constitution: Security (VI)**: Secret detection covers common patterns (AKIA, sk-, password=, etc.).
- [ ] **Constitution: Serverless-First (I)**: S3 + Lambda only.
- [ ] **Coding: Type Hints**: MemoryEntry dataclass fully typed.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
