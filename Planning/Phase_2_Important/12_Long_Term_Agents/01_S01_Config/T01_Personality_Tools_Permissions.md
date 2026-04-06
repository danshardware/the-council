# Task: Personality and Custom Tooling Configuration

## Parent
- **Requirement**: REQ-12 Long-term Agent Features
- **Story**: S01 Long-term Agent Configuration

## Description
Extend agent YAML schema with personality definition (communication style, priorities, decision tendencies), custom tool registration, and permission boundaries.

## Acceptance Criteria
- [ ] **AC-01**: Agent YAML supports `personality` block: communication_style, priorities[], decision_tendencies, role_description.
- [ ] **AC-02**: Personality is injected into agent system prompts and consistently reflected in outputs.
- [ ] **AC-03**: Custom tools can be registered per-agent in YAML (path to tool module).
- [ ] **AC-04**: Permission boundaries defined per-agent: allowed_s3_prefixes[], allowed_commands[], allowed_rooms[], can_spawn_agents (bool).
- [ ] **AC-05**: Permissions enforced at tool invocation — unauthorized access returns clear error.

## QA Checklist
- [ ] pytest tests: personality injection, custom tool loading, permission enforcement.
- [ ] **Constitution: Agent Modularity (II)**: Configuration-driven, not hardcoded.
- [ ] **Constitution: Security (VI)**: Permissions enforced at invocation layer.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
