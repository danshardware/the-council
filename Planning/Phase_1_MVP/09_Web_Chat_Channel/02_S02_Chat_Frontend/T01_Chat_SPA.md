# Task: Chat Frontend SPA

## Parent
- **Requirement**: REQ-09 Web Chat Channel
- **Story**: S02 Chat Frontend

## Description
Single-page web application for the chat interface. Uses HTTP polling to send and receive messages, displays messages with markdown rendering, shows agent status, and handles approval flows.

## Acceptance Criteria
- [ ] **AC-01**: SPA loads from S3/CloudFront and polls the HTTP API for messages.
- [ ] **AC-02**: User can type messages and see agent responses.
- [ ] **AC-03**: Markdown and code blocks render correctly.
- [ ] **AC-04**: Agent status indicators show: thinking, using tool, waiting for approval, idle.
- [ ] **AC-05**: Approval requests surface as interactive buttons (Approve / Reject).
- [ ] **AC-06**: Chat history loads on page open (from S3 via REST API).
- [ ] **AC-07**: Login/auth screen when authentication is enabled.

## QA Checklist
- [ ] Unit tests for message parsing, markdown rendering, polling logic.
- [ ] **Constitution: Serverless-First (I)**: Static hosting on S3. No server-side rendering.
- [ ] **Constitution: Security (VI)**: XSS prevention in message rendering. Auth enforced.
- [ ] **UX Reference**: Clean, functional interface. Compare against OpenClaw WebChat.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
