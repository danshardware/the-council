# Task: Implement Standard Workflow Cycle Flow

## Parent
- **Requirement**: REQ-05 Agent Workflow Engine
- **Story**: S01 Workflow Cycle

## Description
Implement the core workflow cycle as a PocketFlow flow: Think → Pre-Guardrails → Checkpoint → Action → Post-Guardrails → Decide. This is the main execution loop for all agent sessions.

## Acceptance Criteria
- [ ] **AC-01**: `WorkflowCycleFlow` implements all six phases as PocketFlow nodes connected in sequence.
- [ ] **AC-02**: Think phase uses LLM to reason about current state and decide next action.
- [ ] **AC-03**: Pre-guardrails run injection + drift checks.
- [ ] **AC-04**: Checkpoint pauses for approval when the pending action is destructive.
- [ ] **AC-05**: Action phase dispatches to: tool call, communicate, request input, or stop.
- [ ] **AC-06**: Post-guardrails validate the action result.
- [ ] **AC-07**: Decide phase evaluates result and returns: CONTINUE, NEW_TASK, or TERMINATE.
- [ ] **AC-08**: Each phase transition is logged as a distinct action.
- [ ] **AC-09**: The cycle loops (Decide → Think) until TERMINATE or max iterations.

## QA Checklist
- [ ] pytest tests: each phase in isolation, full cycle, phase transitions, action dispatch, termination conditions.
- [ ] **Constitution: Human-in-the-Loop (VIII)**: Checkpoint correctly identifies destructive actions.
- [ ] **Constitution: Observability (V)**: All phase transitions logged.
- [ ] **Constitution: Security (VI)**: Guardrails run every cycle.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
