# Task: Contractor Agent Lifecycle

## Parent
- **Requirement**: REQ-13 Short-term Agents (Contractors)
- **Story**: S01 Contractor Lifecycle

## Description
Implement the full contractor lifecycle: scoped workspace creation, task execution, deliverable production, workspace archival, and resource cleanup.

## Acceptance Criteria
- [ ] **AC-01**: `ContractorAgent` created with: task definition, scope (S3 prefix), budget (tokens + time).
- [ ] **AC-02**: Workspace isolated: contractor can only read/write within its S3 prefix and its session index entry.
- [ ] **AC-03**: On completion, contractor produces deliverable (file(s)) and a summary message.
- [ ] **AC-04**: After completion/failure, workspace is archived to an archive prefix and resources cleaned.
- [ ] **AC-05**: Budget exceeded → agent halted gracefully, workspace archived with partial results.
- [ ] **AC-06**: Progress visible in dashboard as sub-agent of the spawning agent.

## QA Checklist
- [ ] pytest tests: workspace creation/isolation, budget enforcement, cleanup, deliverable production.
- [ ] **Constitution: Serverless-First (I)**: No persistent resources for contractors.
- [ ] **Constitution: Security (VI)**: Workspace isolation enforced.
- [ ] **Constitution: Cost-Conscious (IV)**: Budget enforcement.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
