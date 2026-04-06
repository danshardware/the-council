# REQ-09: Web Chat Channel

## Overview
Direct web-based chat interface for human-agent interaction. This is the critical communication channel for the MVP.

## Source
- [00_The Council.md](../00_The%20Council.md) → Communication Channels (Direct Web Chat — critical)

## Phase
Phase 1 — MVP (Critical)

## Functional Requirements

- **FR-09.01**: Web-based chat UI accessible via browser. Single-page application served from S3 + CloudFront or API Gateway.
- **FR-09.02**: HTTP-based messaging (MVP): POST to send a message, GET to poll for responses. WebSocket can be added in a later iteration.
- **FR-09.03**: Chat sessions map to agent sessions. Creating a new chat starts a new agent session.
- **FR-09.04**: Messages support text, code blocks, and markdown rendering.
- **FR-09.05**: Chat displays agent activity status (thinking, using tool, waiting for approval, etc.).
- **FR-09.06**: Chat history persisted in S3 under `messages/{session_id}/`, loadable on return.
- **FR-09.07**: Human approval requests from agents surface as interactive prompts in the chat.
- **FR-09.08**: Chat triggers agent processing — sending a message invokes the target agent.
- **FR-09.09**: Reference OpenClaw's WebChat UX patterns: clean interface, status indicators, agent session awareness.
- **FR-09.10**: Basic authentication (configurable) to restrict access.

## Non-Functional Requirements

- **NFR-09.01**: Message delivery latency under 2 seconds (human → agent → human via polling).
- **NFR-09.02**: Chat UI loads in under 3 seconds.
- **NFR-09.03**: HTTP endpoints handle Lambda cold starts gracefully.

## Acceptance Criteria

- **AC-09.01**: User opens the web chat, sends a message, and receives an agent response.
- **AC-09.02**: Chat shows real-time agent status (thinking, executing tool, etc.).
- **AC-09.03**: User closes browser, reopens, and sees previous chat history.
- **AC-09.04**: An approval request from an agent appears as an interactive prompt; user approves/rejects.
- **AC-09.05**: Markdown and code blocks render correctly in the chat.
- **AC-09.06**: Unauthenticated users cannot access the chat when authentication is enabled.

## QA Checklist

- [ ] **Unit Tests**: Message handling Lambda, HTTP endpoint handlers, session mapping, auth.
- [ ] **Integration Tests**: End-to-end: user sends message → agent processes → response displayed in chat.
- [ ] **Human Walkthrough**: Open chat in browser, converse with agent, trigger approval flow, verify history persistence.
- [ ] **Constitution: Serverless-First (I)**: API Gateway HTTP, Lambda handlers, S3 hosting. No servers.
- [ ] **Constitution: Security (VI)**: Auth required. Messages treated as untrusted.
- [ ] **Constitution: Observability (V)**: Chat messages logged as part of agent action log.
- [ ] **UX Reference**: Compare against OpenClaw WebChat for UX quality.

## Dependencies

- **Depends on**: REQ-01 (API Gateway, S3, Lambda), REQ-05 (Agent Workflow to process messages)
- **Blocks**: REQ-14 (Discord pattern follows web chat)
