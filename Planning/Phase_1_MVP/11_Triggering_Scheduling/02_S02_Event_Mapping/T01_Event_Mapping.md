# Task: AWS Event Mapping

## Parent
- **Requirement**: REQ-11 Triggering & Scheduling
- **Story**: S02 Event Mapping

## Description
Map AWS events (EventBridge events like S3 uploads, scheduled events) to agent prompts. Event patterns are configurable. 

## Acceptance Criteria
- [ ] **AC-01**: Event mapping definition: event_source, event_pattern, target_agent_id, prompt_template.
- [ ] **AC-02**: Prompt templates can reference event data (e.g., `{{bucket}}`, `{{key}}`).
- [ ] **AC-03**: EventBridge rule created from mapping, targeting the dispatcher Lambda.
- [ ] **AC-04**: An S3 upload triggers the correct agent with the file details in the prompt.
- [ ] **AC-05**: Event mappings stored in config (YAML in S3 `config/events/`).

## QA Checklist
- [ ] pytest tests: event pattern matching, prompt template rendering, event data extraction.
- [ ] **Constitution: Serverless-First (I)**: EventBridge rules only.
- [ ] **Constitution: Security (VI)**: Event payloads treated as untrusted. Template injection prevented.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
