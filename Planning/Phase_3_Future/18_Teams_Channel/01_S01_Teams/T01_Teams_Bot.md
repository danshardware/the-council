# Task: Teams Bot Integration

## Parent
- **Requirement**: REQ-18 Teams Channel
- **Story**: S01 Teams Integration

## Description
Build a Microsoft Teams bot that connects to The Council via API Gateway. Mentions, 1:1 chats, and adaptive cards trigger agent interactions.

## Acceptance Criteria
- [ ] **AC-01**: Teams bot registered in Azure Bot Service with messaging endpoint pointing to API Gateway.
- [ ] **AC-02**: Lambda handler receives Teams activity, maps to channel-agnostic message format.
- [ ] **AC-03**: Agent responses posted back via Bot Framework REST API.
- [ ] **AC-04**: Adaptive Cards for structured responses (status, approvals, agent lists).
- [ ] **AC-05**: 1:1 and group chat support.

## QA Checklist
- [ ] pytest tests: activity parsing, card rendering, response posting.
- [ ] **Constitution: Security (VI)**: Bot Framework auth token validated.
- [ ] **Constitution: Observability (V)**: All Teams activities logged.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
