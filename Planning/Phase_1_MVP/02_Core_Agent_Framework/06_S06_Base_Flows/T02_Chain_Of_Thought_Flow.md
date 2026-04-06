# Task: Chain of Thought Flow

## Parent
- **Requirement**: REQ-02 Core Agent Framework
- **Story**: S06 Base Flows

## Description
Implement Chain of Thought as a PocketFlow flow: breaks a complex problem into reasoning steps, executes each step sequentially, and aggregates insights into a final answer.

## Acceptance Criteria
- [ ] **AC-01**: CoT flow decomposes a problem into numbered reasoning steps.
- [ ] **AC-02**: Each step's reasoning is logged individually.
- [ ] **AC-03**: Final answer synthesizes insights from all steps.
- [ ] **AC-04**: Flow is usable as a sub-flow within other flows (composable).

## QA Checklist
- [ ] pytest tests: step decomposition, sequential execution, aggregation, composability.
- [ ] **Constitution: Observability (V)**: Each reasoning step logged.
- [ ] **Constitution: Simplicity (VII)**: Simple sequential step pattern. No over-engineering.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
