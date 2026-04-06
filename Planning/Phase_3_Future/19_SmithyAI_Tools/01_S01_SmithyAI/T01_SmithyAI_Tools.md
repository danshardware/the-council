# Task: SmithyAI KV, Docs, and Vector Store Tools

## Parent
- **Requirement**: REQ-19 SmithyAI Tools Integration
- **Story**: S01 SmithyAI Tools

## Description
Integrate SmithyAI tool endpoints as BedrockTool instances: KV Store (persistent key-value), Documentation store (RAG), and Vector Store (embeddings search).

## Acceptance Criteria
- [ ] **AC-01**: `smithy_kv_get(key)`, `smithy_kv_put(key, value)`, `smithy_kv_delete(key)` map to SmithyAI KV API.
- [ ] **AC-02**: `smithy_doc_search(query, collection)` queries SmithyAI Documentation endpoint with RAG.
- [ ] **AC-03**: `smithy_vector_search(query, namespace, top_k)` queries SmithyAI Vector Store.
- [ ] **AC-04**: All tools registered as BedrockTool instances and appear in agent tool lists.
- [ ] **AC-05**: SmithyAI API credentials stored in environment variables.

## QA Checklist
- [ ] pytest tests: tool registration, request/response mapping, error handling.
- [ ] **Constitution: Security (VI)**: API credentials from environment, not hardcoded.
- [ ] **Constitution: Cost (IV)**: Document token costs for vector/doc searches.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
