# Task: Token Budget Tracking and Enforcement

## Parent
- **Requirement**: REQ-02 Core Agent Framework
- **Story**: S04 Model Routing & Budget

## Description
Track token usage per-call, per-session, per-agent. Enforce configurable budget limits that halt execution when exceeded.

## Acceptance Criteria
- [ ] **AC-01**: `TokenTracker` accumulates input/output/total tokens per-call, per-session, per-agent.
- [ ] **AC-02**: Budget limits configurable per-session and per-agent in YAML config (S3 `config/` prefix).
- [ ] **AC-03**: When budget is exceeded, a `BudgetExceededError` is raised and the session halts gracefully.
- [ ] **AC-04**: Token usage is logged as part of action log entries (S3 JSONL).
- [ ] **AC-05**: Budget status (used/remaining) is queryable at any time during a session.

## QA Checklist
- [ ] pytest tests: accumulation, budget enforcement, graceful halt, query status.
- [ ] **Constitution: Cost-Conscious (IV)**: Budget enforcement prevents runaway costs.
- [ ] **Constitution: Observability (V)**: Usage tracked and logged.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
