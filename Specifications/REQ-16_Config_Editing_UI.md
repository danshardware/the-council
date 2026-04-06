# REQ-16: Config & Resource Editing UI

## Overview
Web-based interface for editing agent configurations, system settings, and resources stored in S3/CodeCommit.

## Source
- [00_The Council.md](../00_The%20Council.md) → UI/UX (Allow editing of config files, VS Code web ideal)

## Phase
Phase 2 — Important

## Functional Requirements

- **FR-16.01**: Web UI for editing agent YAML configuration files with syntax highlighting and validation.
- **FR-16.02**: Web UI for editing system configuration (schedules, room settings, permissions).
- **FR-16.03**: Resource browser: navigate S3 file structure, preview text files, upload/download files.
- **FR-16.04**: For code/config editing, provide a VS Code Web-compatible experience if feasible (files staged to temporary location for editing, then synced back).
- **FR-16.05**: Edit history with undo capability (leveraging S3 versioning).
- **FR-16.06**: Validation on save: YAML schema validation, permission checks.

## Acceptance Criteria

- **AC-16.01**: User edits an agent YAML file in the web UI and the changes take effect.
- **AC-16.02**: Invalid YAML shows validation errors before save.
- **AC-16.03**: User browses S3 files, opens one for editing, saves changes, and sees them reflected.
- **AC-16.04**: Previous versions of a file can be viewed and restored.

## QA Checklist

- [ ] **Unit Tests**: YAML validation, S3 operations, version management.
- [ ] **Integration Tests**: Edit config → save → agent loads new config → behavior changes.
- [ ] **Human Walkthrough**: Edit agent config, save, verify agent behavior changes. Browse and edit S3 files.
- [ ] **Constitution: Security (VI)**: Auth required. Edit operations logged.
- [ ] **Constitution: Simplicity (VII)**: Simple editor first, VS Code Web only if justified.

## Dependencies

- **Depends on**: REQ-01 (S3, API Gateway), REQ-10 (Dashboard provides the UI shell)
- **Blocks**: None
