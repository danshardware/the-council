# Task: Activity Log API

## Parent
- **Requirement**: REQ-10 Activity Dashboard
- **Story**: S01 Activity API

## Description
REST API endpoints for fetching agent activity data: list agents, list sessions, get session timeline, filter/search activities.

## Acceptance Criteria
- [ ] **AC-01**: `GET /agents` returns list of agents with recent session counts.
- [ ] **AC-02**: `GET /agents/{id}/sessions` returns sessions for an agent, sorted by recency.
- [ ] **AC-03**: `GET /sessions/{id}/timeline` returns the action timeline for a session.
- [ ] **AC-04**: Timeline entries include: action_type, timestamp, summary, detail (expandable), sub_session_id (if spawned).
- [ ] **AC-05**: `GET /sessions/{id}/summary` returns resource table and action summary.
- [ ] **AC-06**: Query params support filtering by action_type, time_range, and resource.
- [ ] **AC-07**: Polling endpoint: `GET /sessions/{id}/timeline?after={timestamp}` returns new actions since timestamp.

## QA Checklist
- [ ] pytest tests: each endpoint, filtering, pagination, real-time subscription.
- [ ] **Constitution: Serverless-First (I)**: API Gateway + Lambda.
- [ ] **Constitution: Observability (V)**: This IS the observability surface.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
