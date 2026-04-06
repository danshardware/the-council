# Task: Agent List and Session Browser

## Parent
- **Requirement**: REQ-10 Activity Dashboard
- **Story**: S02 Dashboard Frontend

## Description
Dashboard panel showing the list of agents with session counts and status. Clicking an agent shows its sessions sorted by recency.

## Acceptance Criteria
- [ ] **AC-01**: Agent list panel shows all agents with name, status, and recent session count.
- [ ] **AC-02**: Clicking an agent expands/navigates to its session list, sorted by most recent.
- [ ] **AC-03**: Sessions show: start time, duration, status (active/complete/error), action count.
- [ ] **AC-04**: Static SPA served from S3 `web-ui/` prefix.

## QA Checklist
- [ ] Frontend component tests: agent list renders, session list renders, sorting works.
- [ ] **Constitution: Serverless-First (I)**: Static hosting on S3.
- [ ] **UX Reference**: Clean layout inspired by OpenClaw Control UI.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
