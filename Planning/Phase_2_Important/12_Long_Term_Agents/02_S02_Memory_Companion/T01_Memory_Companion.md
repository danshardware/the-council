# Task: Memory-Writing Companion Agent

## Parent
- **Requirement**: REQ-12 Long-term Agent Features
- **Story**: S02 Memory Companion

## Description
A companion agent that runs at session end (or periodically during long sessions) to review activity and create new memory entries summarizing decisions, facts, and outcomes.

## Acceptance Criteria
- [ ] **AC-01**: Memory companion triggers at session end for long-term agents.
- [ ] **AC-02**: Companion reviews session action log and conversation history.
- [ ] **AC-03**: Companion creates structured memory entries using the Memory Extraction Node.
- [ ] **AC-04**: Created memories include: content, keywords, context, and are assigned to the parent agent.
- [ ] **AC-05**: Uses a cheap model for cost efficiency.
- [ ] **AC-06**: For long sessions (>50 actions), companion runs periodically (configurable interval).

## QA Checklist
- [ ] pytest tests: trigger conditions, session review, memory creation, periodic trigger.
- [ ] **Constitution: Cost-Conscious (IV)**: Cheap model.
- [ ] **Constitution: Observability (V)**: Companion actions logged.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
