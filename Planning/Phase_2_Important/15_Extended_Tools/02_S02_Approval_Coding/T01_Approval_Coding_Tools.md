# Task: Approval and Coding Tools

## Parent
- **Requirement**: REQ-15 Extended Tools Suite
- **Story**: S02 Approval & Coding

## Description
Implement approval-gated tools and the coding tools (lint, test, format, refactor) that agents can invoke.

## Acceptance Criteria
- [ ] **AC-01**: `get_approval(action, reason)` pauses agent until human approves/rejects via UI or chat.
- [ ] **AC-02**: Approval timeout configurable with default-deny policy.
- [ ] **AC-03**: Coding tools: `lint(path)`, `run_tests(path)`, `format_code(path)`, `refactor(path, instruction)`.
- [ ] **AC-04**: Coding tools operate within the agent's permitted workspace scope.
- [ ] **AC-05**: All approvals and coding tool invocations logged.

## QA Checklist
- [ ] pytest tests: approval flow, coding tool outputs.
- [ ] **Constitution: Human-in-the-Loop (VIII)**: Approval blocks irreversible actions.
- [ ] **Constitution: Security (VI)**: Coding tools respect workspace boundaries.
- [ ] **Constitution: Testing (III)**: Tests first for each tool.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
