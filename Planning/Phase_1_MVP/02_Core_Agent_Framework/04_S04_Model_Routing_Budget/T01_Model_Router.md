# Task: Model Routing and Cost Tiers

## Parent
- **Requirement**: REQ-02 Core Agent Framework
- **Story**: S04 Model Routing & Budget

## Description
Implement model selection logic that routes requests to appropriate cost-tier models based on task type. Cheap models for extraction/classification/guardrails, expensive for reasoning/planning.

## Acceptance Criteria
- [ ] **AC-01**: `ModelRouter` class accepts a task type and returns the appropriate model ID.
- [ ] **AC-02**: Task types defined: REASONING, PLANNING, CREATIVE, EXTRACTION, CLASSIFICATION, GUARDRAIL, FORMATTING.
- [ ] **AC-03**: Model tier configuration stored in system config (YAML in S3 `config/` prefix). Easily changeable.
- [ ] **AC-04**: Per-agent model override is respected (agent YAML specifies preferred model).
- [ ] **AC-05**: Per-node model override is supported (specific flow node can force a model).

## QA Checklist
- [ ] pytest tests: routing for each task type, agent override, node override, default fallback.
- [ ] **Constitution: Cost-Conscious (IV)**: Cheap models used for routine tasks by default.
- [ ] **Constitution: Simplicity (VII)**: Simple lookup table, not a complex ML-based router.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
