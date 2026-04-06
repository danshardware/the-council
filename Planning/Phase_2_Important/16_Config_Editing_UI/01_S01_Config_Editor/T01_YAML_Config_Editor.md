# Task: YAML Config Editor

## Parent
- **Requirement**: REQ-16 Config Editing UI
- **Story**: S01 Config Editor

## Description
Build a web-based YAML editor for agent definitions, workflow configs, and system settings. Support schema validation, syntax highlighting, and live preview.

## Acceptance Criteria
- [ ] **AC-01**: YAML editor loads and saves agent definition files from S3.
- [ ] **AC-02**: Schema-driven validation shows inline errors.
- [ ] **AC-03**: Editor supports agent YAML, workflow YAML, and trigger YAML schemas.
- [ ] **AC-04**: Changes saved via API Gateway → Lambda → S3 with version history.
- [ ] **AC-05**: Resource browser lists all config files with filter/search.

## QA Checklist
- [ ] pytest tests: Lambda handler for config CRUD.
- [ ] Frontend tests: editor renders, validates, saves.
- [ ] **Constitution: Observability (V)**: Config changes logged with who/when/what.
- [ ] **Constitution: Security (VI)**: Auth required for config writes.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
