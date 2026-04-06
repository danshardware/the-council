# Task: YAML Agent Definition Schema

## Parent
- **Requirement**: REQ-02 Core Agent Framework
- **Story**: S02 Agent YAML Definition

## Description
Define and implement the YAML schema for agent definitions. Include validation, loading, and a sample agent definition.

## Acceptance Criteria
- [ ] **AC-01**: YAML schema defined with fields: name, description, model_id, system_prompts, tools, permissions, flows, personality, max_iterations, budget_tokens.
- [ ] **AC-02**: YAML loader parses a valid definition and returns a typed AgentDefinition dataclass.
- [ ] **AC-03**: Invalid YAML (missing required fields, wrong types) produces clear validation errors.
- [ ] **AC-04**: A sample agent YAML file demonstrates all schema features.
- [ ] **AC-05**: Optional fields have sensible defaults.

## QA Checklist
- [ ] pytest tests: valid YAML loads, missing fields error, wrong types error, defaults applied.
- [ ] **Constitution: Agent Modularity (II)**: Schema is declarative, not imperative.
- [ ] **Constitution: Simplicity (VII)**: Schema only includes fields needed now. No speculative fields.
- [ ] **Coding: Type Hints**: AgentDefinition dataclass fully typed.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
