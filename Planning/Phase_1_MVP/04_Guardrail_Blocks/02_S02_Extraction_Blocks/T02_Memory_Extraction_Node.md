# Task: Memory Extraction Node

## Parent
- **Requirement**: REQ-04 Guardrail Blocks
- **Story**: S02 Extraction Blocks

## Description
PocketFlow node that analyzes conversations/actions and identifies information worth persisting in agent memory. Returns candidate memory entries with keywords and context.

## Acceptance Criteria
- [ ] **AC-01**: `MemoryExtractionNode` accepts a conversation or action history and returns candidate memory entries.
- [ ] **AC-02**: Each candidate has: content, keywords[], related_context, importance_score, suggested_scope (permanent/shared/temporary).
- [ ] **AC-03**: Filters out trivial or redundant information.
- [ ] **AC-04**: Does not suggest storing passwords or secrets.
- [ ] **AC-05**: Uses a cheap model.

## QA Checklist
- [ ] pytest tests: extraction from conversations, importance scoring, secret filtering, scope suggestion.
- [ ] **Constitution: Security (VI)**: Secrets not extracted as memory candidates.
- [ ] **Constitution: Cost-Conscious (IV)**: Cheap model used.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
