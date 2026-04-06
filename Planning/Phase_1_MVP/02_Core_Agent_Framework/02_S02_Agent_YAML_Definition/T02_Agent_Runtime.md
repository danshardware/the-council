# Task: Agent Runtime and Session Management

## Parent
- **Requirement**: REQ-02 Core Agent Framework
- **Story**: S02 Agent YAML Definition

## Description
Implement the agent runtime that loads a definition (YAML or programmatic), creates sessions, manages session state, and handles lifecycle (create → initialize → run → teardown).

## Acceptance Criteria
- [ ] **AC-01**: `AgentRuntime` class loads an `AgentDefinition` and creates runnable agent instances.
- [ ] **AC-02**: Multiple sessions created from the same agent have isolated state.
- [ ] **AC-03**: Agent lifecycle methods: `create()`, `start_session()`, `run()`, `end_session()`, `teardown()`.
- [ ] **AC-04**: Programmatic agent creation (without YAML) works via `AgentDefinition` constructor.
- [ ] **AC-05**: Session state is serializable for Lambda cold-start recovery.

## QA Checklist
- [ ] pytest tests: lifecycle methods, session isolation, serialization/deserialization.
- [ ] **Constitution: Agent Modularity (II)**: Agents independently instantiable and testable.
- [ ] **Constitution: Serverless-First (I)**: Session state serializable for stateless Lambda.
- [ ] **Coding: Docstrings**: All public lifecycle methods documented.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
