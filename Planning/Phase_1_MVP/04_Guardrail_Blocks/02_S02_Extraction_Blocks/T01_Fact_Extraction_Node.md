# Task: Fact Extraction Node

## Parent
- **Requirement**: REQ-04 Guardrail Blocks
- **Story**: S02 Extraction Blocks

## Description
PocketFlow node that extracts structured facts (entities, relationships, data points) from unstructured text.

## Acceptance Criteria
- [ ] **AC-01**: `FactExtractionNode` accepts text and returns structured JSON: entities[], relationships[], data_points[].
- [ ] **AC-02**: Each entity has: name, type, confidence.
- [ ] **AC-03**: Relationships link entities with a description.
- [ ] **AC-04**: Works on conversational text, reports, and mixed content.
- [ ] **AC-05**: Uses a cheap model.

## QA Checklist
- [ ] pytest tests: entity extraction, relationship detection, various text types, empty input.
- [ ] **Constitution: Cost-Conscious (IV)**: Cheap model used.
- [ ] **Coding: Type Hints**: Output schema fully typed.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
