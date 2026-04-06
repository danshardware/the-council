# Task: Agent State Checkpoint (Serialize to S3)

## Parent
- **Requirement**: REQ-02 Core Agent Framework
- **Story**: S05 Base Nodes

## Description
Agents need to checkpoint their state so they can be resumed after Lambda timeout, human-in-the-loop pauses, or SQS-driven restarts. Serialize the agent's shared store (PocketFlow state) to S3 as JSON under a session ID key, and restore from it on resume.

## Acceptance Criteria
- [ ] **AC-01**: `StateCheckpointNode` serializes the agent's shared store to S3 at `agent-state/{session_id}/checkpoint.json`.
- [ ] **AC-02**: `StateResumeNode` loads a checkpoint from S3 and restores the shared store.
- [ ] **AC-03**: Checkpoint includes: session_id, agent_id, current_node, shared_store snapshot, timestamp.
- [ ] **AC-04**: Checkpoints are versioned — multiple checkpoints per session are preserved (timestamped keys).
- [ ] **AC-05**: State serialization handles all common Python types (str, int, float, list, dict, None, dataclasses).

## QA Checklist
- [ ] pytest tests: serialize/deserialize round-trip, S3 read/write, type handling edge cases.
- [ ] **Constitution: Security (VI)**: Checkpoint data must not contain secrets. Redact before serialization.
- [ ] **Constitution: Observability (V)**: Checkpoint creation logged.
- [ ] **Constitution: Simplicity (VII)**: JSON serialization. No pickle.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
