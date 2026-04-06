# REQ-13: Short-term Agents (Contractors)

## Overview
Agents assigned well-scoped tasks with dedicated workspaces. They are created on demand, complete their work, and are torn down. Think of them as contractors.

## Source
- [00_The Council.md](../00_The%20Council.md) → Actors (Short-term Agents: Contractors), Agents: Functional Requirements (Functional Agents)

## Phase
Phase 2 — Important

## Functional Requirements

- **FR-13.01**: Short-term agents are created with a specific task definition, workspace scope, and time/token budget.
- **FR-13.02**: Each short-term agent gets a workspace: a scoped S3 prefix and a session index entry in DynamoDB.
- **FR-13.03**: Short-term agents perform a single, well-defined function: spot inconsistencies, research a topic, write code, etc.
- **FR-13.04**: On completion, short-term agents produce a deliverable (file, report, code) and a summary.
- **FR-13.05**: After completion, the workspace is archived (moved to archive prefix) and the agent is torn down.
- **FR-13.06**: Short-term agents can be spawned by long-term agents or by the triggering system.
- **FR-13.07**: Progress of short-term agents is visible in the activity dashboard.
- **FR-13.08**: Short-term agents can request clarification from their parent agent or from humans.

## Acceptance Criteria

- **AC-13.01**: A long-term agent spawns a contractor to research a topic. The contractor returns a summary.
- **AC-13.02**: The contractor's workspace is isolated — it cannot access files outside its scope.
- **AC-13.03**: After completion, the workspace is archived and the contractor's resources are cleaned up.
- **AC-13.04**: A contractor that exceeds its budget is halted with a budget-exceeded status.
- **AC-13.05**: Contractor progress is visible in the dashboard.

## QA Checklist

- [ ] **Unit Tests**: Workspace creation/scoping, lifecycle management, budget enforcement, cleanup.
- [ ] **Integration Tests**: Spawn contractor → execute task → return result → archive → cleanup.
- [ ] **Human Walkthrough**: Spawn a contractor, observe it working in the dashboard, verify deliverable and cleanup.
- [ ] **Constitution: Serverless-First (I)**: No persistent resources for contractors.
- [ ] **Constitution: Security (VI)**: Workspace isolation enforced.
- [ ] **Constitution: Cost-Conscious (IV)**: Budget enforcement prevents runaway costs.

## Dependencies

- **Depends on**: REQ-02 (Agent Framework), REQ-05 (Workflow), REQ-12 (Long-term agents spawn contractors)
- **Blocks**: None
