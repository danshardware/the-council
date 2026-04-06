# Task: Session Timeline with Action Icons

## Parent
- **Requirement**: REQ-10 Activity Dashboard
- **Story**: S02 Dashboard Frontend

## Description
Timeline view for a session showing all actions in chronological order. Each action type has a distinct icon. Actions expand/collapse to show detail.

## Acceptance Criteria
- [ ] **AC-01**: Timeline displays actions chronologically with icons per type: 🧠 thinking, 🔧 tool, 🛡️ guardrail, ⏸️ checkpoint, 💬 communication, ❌ error, ✅ completion.
- [ ] **AC-02**: Actions expand/collapse to show full detail (inputs, outputs, duration, cost).
- [ ] **AC-03**: Default expand/collapse state is configurable per action type.
- [ ] **AC-04**: Sub-agent links navigate to the sub-agent's session timeline.

## QA Checklist
- [ ] Frontend component tests: timeline renders, icons correct, expand/collapse works, sub-agent links navigate.
- [ ] **Constitution: Observability (V)**: All logged actions visible in timeline.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
