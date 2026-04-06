# Task: Action Logging System

## Parent
- **Requirement**: REQ-02 Core Agent Framework
- **Story**: S01 PocketFlow Integration

## Description
Implement the structured action logging system that records every agent action with: agent ID, session ID, action type, timestamp, inputs, outputs, and token cost. Logs write to S3 bucket under the 'agent-logs/' prefix.

## Acceptance Criteria
- [ ] **AC-01**: Action log entries contain: agent_id, session_id, action_type, timestamp, inputs, outputs, duration_ms, token_cost.
- [ ] **AC-02**: Logging function writes to S3 under the agent-logs/ prefix with all actions being added as multiple JSONL files under a sessionID prefixed by session ID. (e.g. `agent-logs/11111111-2222-3333-444444444444/20260301123456.jsonl`)
- [ ] **AC-03**: Action types defined as enum: THINKING, TOOL_CALL, GUARDRAIL, CHECKPOINT, COMMUNICATION, ERROR, COMPLETION.

## QA Checklist
- [ ] pytest tests for log creation, S3 writes, enum validation.
- [ ] **Constitution: Observability (V)**: Every action type is loggable.
- [ ] **Constitution: Security (VI)**: No secrets logged. Sensitive content redacted.
- [ ] **Coding: PEP 8, Type Hints**: ActionLog dataclass fully typed.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
