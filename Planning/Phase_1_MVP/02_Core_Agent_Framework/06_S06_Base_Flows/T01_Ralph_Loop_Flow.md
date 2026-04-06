# Task: Ralph Loop Flow

## Parent
- **Requirement**: REQ-02 Core Agent Framework
- **Story**: S06 Base Flows

## Description
Implement the Ralph Loop as a PocketFlow flow: iteratively reads a task list, picks a task, implements it, validates, commits progress, and loops until all tasks complete or max iterations reached.

## Acceptance Criteria
- [ ] **AC-01**: Ralph Loop flow reads tasks from a progress file (or shared store).
- [ ] **AC-02**: Each iteration: pick task → implement → validate → update progress → commit.
- [ ] **AC-03**: Loop terminates when all tasks are marked complete.
- [ ] **AC-04**: Loop terminates when max iterations reached, with partial progress preserved.
- [ ] **AC-05**: Each iteration is logged as a distinct action with task ID and result.
- [ ] **AC-06**: Progress state persists across Lambda invocations (serializable to S3 via StateCheckpointNode).

## QA Checklist
- [ ] pytest tests: task selection, iteration, completion detection, max iterations, progress persistence.
- [ ] **Constitution: Observability (V)**: Each iteration logged.
- [ ] **Constitution: Cost-Conscious (IV)**: Iteration count tracked. Budget awareness.
- [ ] **Constitution: Test-First (III)**: Tests define expected iteration behavior before implementation.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
