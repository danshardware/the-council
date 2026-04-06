# Task: Design Use Cases, Schema, and Sample Flows

## Parent
- **Requirement**: REQ-02 Core Agent Framework
- **Story**: S00 Design (Human Collaboration)

## Description
Before implementing anything, work with a human to design the system. Define all agent use cases, design the data schemas (agent definitions, sessions, memory entries, messages, action logs), and map out sample end-to-end flows showing how agents process requests through PocketFlow.

This is a design-only task. No code is written. The output is documentation that guides all subsequent implementation.

## Acceptance Criteria
- [ ] **AC-01**: Catalogue of agent use cases: at least 5 concrete scenarios (e.g., "research agent answering a question", "coding agent implementing a feature", "monitor agent checking system health").
- [ ] **AC-02**: Data schema document covering: AgentDefinition (YAML), SessionState, ActionLogEntry, MemoryEntry, Message, ScheduleConfig.
- [ ] **AC-03**: At least 3 sample flows diagrammed as node/flow graphs showing the PocketFlow execution path (e.g., Ralph Loop flow, simple Q&A flow, multi-agent delegation flow).
- [ ] **AC-04**: S3 key structure documented: how each data type maps to S3 prefixes and object keys.
- [ ] **AC-05**: DynamoDB table design for session indexes (partition key, sort key, GSIs, access patterns).
- [ ] **AC-06**: Human has reviewed and approved all schemas and flows.

## QA Checklist
- [ ] Schemas cover every data type referenced in REQ-02 through REQ-11.
- [ ] Sample flows demonstrate the core PocketFlow patterns (Node prep/exec/post, Flow linking).
- [ ] S3 key structure avoids hot partitions. Keys are well-distributed.
- [ ] **Constitution: Simplicity (VII)**: No speculative schema fields. Only what's needed for MVP.
- [ ] **Constitution: Observability (V)**: ActionLogEntry schema supports the dashboard queries.
- [ ] **Constitution: Security (VI)**: No secrets in any schema field.

## Progress Checklist
- [ ] Task started
- [ ] Use cases catalogued
- [ ] Schemas designed
- [ ] Sample flows diagrammed
- [ ] S3 key structure documented
- [ ] Human review and approval
- [ ] Task complete
