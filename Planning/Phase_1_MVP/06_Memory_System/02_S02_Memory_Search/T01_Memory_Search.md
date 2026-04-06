# Task: Memory Search (Keyword and Semantic via S3 Vector Buckets)

## Parent
- **Requirement**: REQ-06 Memory System
- **Story**: S02 Memory Search

## Description
Implement keyword-based and semantic (embedding-based) search over memory entries stored in S3. Use S3's vector bucket capabilities (or client-side cosine similarity over stored embeddings) for fuzzy search by keywords and phrases. Return ranked results with relevance scores.

## Acceptance Criteria
- [ ] **AC-01**: Keyword search scans memory entry metadata (keywords field) and returns matching entries.
- [ ] **AC-02**: Semantic search generates an embedding for the query (Bedrock Titan Embeddings) and finds similar entries by cosine similarity against stored embedding vectors.
- [ ] **AC-03**: Results are ranked by relevance score (keyword match count or cosine similarity).
- [ ] **AC-04**: Search respects scope: agents only see their own + shared memories (not other agents' permanent).
- [ ] **AC-05**: Hybrid search combines keyword and semantic results.
- [ ] **AC-06**: Memory entries under `memory/{agent_id}/` and `memory/shared/` are searchable.

## QA Checklist
- [ ] pytest tests: keyword matching, embedding generation, cosine similarity ranking, scope filtering, hybrid search.
- [ ] **Constitution: Serverless-First (I)**: S3 + Lambda. No persistent search servers or vector DBs.
- [ ] **Constitution: Cost-Conscious (IV)**: Embedding model is cheap. Cache embeddings on memory entries.
- [ ] **Constitution: Simplicity (VII)**: Start simple. Client-side similarity unless S3 vector features handle it natively.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
