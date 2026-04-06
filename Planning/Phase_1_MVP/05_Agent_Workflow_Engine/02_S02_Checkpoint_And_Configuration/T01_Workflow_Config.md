# Task: Workflow Configuration and Phase Control

## Parent
- **Requirement**: REQ-05 Agent Workflow Engine
- **Story**: S02 Checkpoint and Configuration

## Description
Make the workflow cycle configurable: agents can skip optional phases, set max iterations, and define which actions are considered destructive.

## Acceptance Criteria
- [ ] **AC-01**: Workflow config in agent YAML: `skip_phases: [checkpoint]`, `max_iterations: 50`, `destructive_actions: [file_delete, execute]`.
- [ ] **AC-02**: Skipping checkpoint phase allows all actions without approval (for trusted/internal agents).
- [ ] **AC-03**: Max iterations configurable per-agent. System default of 100.
- [ ] **AC-04**: Destructive action list is configurable. Default list includes: file_delete, execute, external_communication.
- [ ] **AC-05**: Configuration validation rejects invalid phase names or negative iteration limits.

## QA Checklist
- [ ] pytest tests: config parsing, phase skipping, max iterations, destructive list, validation.
- [ ] **Constitution: Human-in-the-Loop (VIII)**: Destructive defaults are safe. Skipping requires explicit opt-in.
- [ ] **Constitution: Simplicity (VII)**: Config is declarative. No complex rule engines.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
