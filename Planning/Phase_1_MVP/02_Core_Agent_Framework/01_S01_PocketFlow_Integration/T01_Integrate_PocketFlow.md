# Task: Integrate PocketFlow Library

## Parent
- **Requirement**: REQ-02 Core Agent Framework
- **Story**: S01 PocketFlow Integration

## Description
Fork or vendor PocketFlow (100-line core) into the project. Resolve typing issues. Add type annotations throughout. Ensure it works with Python 3.14.

## Acceptance Criteria
- [ ] **AC-01**: PocketFlow source code vendored into `council/pocketflow/` with typing issues resolved.
- [ ] **AC-02**: All PocketFlow classes (`Node`, `Flow`, `BatchNode`, `BatchFlow`) have complete type annotations.
- [ ] **AC-03**: PocketFlow's existing test suite passes on Python 3.14.
- [ ] **AC-04**: A simple test flow (Node A → Node B → Node C) executes correctly.

## QA Checklist
- [ ] pytest passes for all PocketFlow tests.
- [ ] Type checker (mypy or pyright) reports no errors on the PocketFlow module.
- [ ] **Constitution: Simplicity (VII)**: Minimal changes to PocketFlow core. Only fix types, don't restructure.
- [ ] **Constitution: Test-First (III)**: Tests pass before and after type fixes.
- [ ] **Coding: Type Hints**: Complete type annotations on all public APIs.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough waived and unecessary for this task
