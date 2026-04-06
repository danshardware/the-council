# Task: Execute Tool

## Parent
- **Requirement**: REQ-08 Core Tools
- **Story**: S02 Execute and SubAgent

## Description
Tool for executing commands in a restricted environment. Configurable allowlist/denylist, timeout enforcement, output capture.

## Acceptance Criteria
- [ ] **AC-01**: `execute(command, args, timeout)` runs a command and returns stdout, stderr, exit_code.
- [ ] **AC-02**: Command allowlist: only explicitly permitted commands can run.
- [ ] **AC-03**: Command denylist: explicitly blocked commands always rejected (e.g., `rm -rf /`).
- [ ] **AC-04**: Timeout enforcement: commands killed after timeout (default 30s, max 300s).
- [ ] **AC-05**: Execution logged with command, args, output (truncated if large), and duration.
- [ ] **AC-06**: Marked as destructive action for checkpoint system.

## QA Checklist
- [ ] pytest tests: allowed command, denied command, timeout, output capture, logging.
- [ ] **Constitution: Security (VI)**: Allowlist-based. No arbitrary execution.
- [ ] **Constitution: Human-in-the-Loop (VIII)**: Marked destructive for checkpoint.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
