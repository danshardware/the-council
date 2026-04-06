# Task: Discord Bot Integration

## Parent
- **Requirement**: REQ-14 Discord Channel
- **Story**: S01 Discord Integration

## Description
Lambda-based Discord bot that receives webhook events, routes messages to agents, and posts responses. Supports slash commands and interactive components.

## Acceptance Criteria
- [ ] **AC-01**: Discord bot registered with slash commands (`/ask`, `/status`, `/approve`).
- [ ] **AC-02**: Webhook handler (Lambda behind API Gateway) processes Discord interaction events.
- [ ] **AC-03**: Messages route to appropriate agent, agent response posted back to channel.
- [ ] **AC-04**: Approval requests shown as Discord buttons.
- [ ] **AC-05**: DM security: pairing/allowlist model.
- [ ] **AC-06**: Bot token stored in environment variable, not in code.

## QA Checklist
- [ ] pytest tests: webhook signature validation, message routing, response formatting, auth.
- [ ] **Constitution: Security (VI)**: Token in env. Input untrusted. Webhook signature verified.
- [ ] **Constitution: Serverless-First (I)**: Webhook + Lambda, not a persistent bot process.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
