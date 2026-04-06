# Task: Goal Drift Detection Node

## Parent
- **Requirement**: REQ-04 Guardrail Blocks
- **Story**: S01 Prompt Injection Detection

## Description
PocketFlow node that compares the agent's current activity against its assigned goals to detect when the agent has strayed from its objectives.

## Acceptance Criteria
- [ ] **AC-01**: `GoalDriftNode` accepts current state (last N actions + current intent) and original goals.
- [ ] **AC-02**: Returns: drift_score (0-1), classification (on-track/drifting/off-track), reasoning.
- [ ] **AC-03**: An agent given a "research marketing" task that starts writing code is flagged as off-track.
- [ ] **AC-04**: An agent progressing through sub-steps of its goal is correctly identified as on-track.
- [ ] **AC-05**: Uses a cheap model.

## QA Checklist
- [ ] pytest tests: on-track scenarios, drift scenarios, edge cases.
- [ ] **Constitution: Cost-Conscious (IV)**: Cheap model used.
- [ ] **Constitution: Observability (V)**: Drift assessments logged.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
