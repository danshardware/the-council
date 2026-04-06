# Task: HTTP Chat Handlers

## Parent
- **Requirement**: REQ-09 Web Chat Channel
- **Story**: S01 HTTP Backend

## Description
Lambda handlers for HTTP-based chat (no WebSocket for MVP). POST to send a message, GET to poll for responses. Each component deploys its own API Gateway routes and Lambda via Terraform alongside this code.

## Acceptance Criteria
- [ ] **AC-01**: `POST /chat/sessions` creates a new chat session and returns session_id.
- [ ] **AC-02**: `POST /chat/sessions/{id}/messages` sends a message, invokes the agent, returns message_id.
- [ ] **AC-03**: `GET /chat/sessions/{id}/messages?after={message_id}` returns new messages since the given ID (polling).
- [ ] **AC-04**: Agent responses are stored in S3 under `messages/{session_id}/` as JSON and returned on poll.
- [ ] **AC-05**: Agent status (thinking, tool use, etc.) returned as status messages in the poll response.
- [ ] **AC-06**: Chat history persisted in S3, loadable via `GET /chat/sessions/{id}/messages`.
- [ ] **AC-07**: Basic authentication (configurable) to restrict access.
- [ ] **AC-08**: Terraform deploys API Gateway routes + Lambda + IAM alongside this code.

## QA Checklist
- [ ] pytest tests: session creation, message posting, polling, history loading, auth.
- [ ] **Constitution: Serverless-First (I)**: API Gateway + Lambda.
- [ ] **Constitution: Security (VI)**: Auth required. Messages treated as untrusted.
- [ ] **Constitution: Observability (V)**: Chat messages logged as agent actions.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
