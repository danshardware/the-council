# REQ-14: Discord Channel

## Overview
Discord bot integration enabling human-agent interaction via Discord servers.

## Source
- [00_The Council.md](../00_The%20Council.md) → Communication Channels (Discord — important)

## Phase
Phase 2 — Important

## Functional Requirements

- **FR-14.01**: Discord bot connects to configured servers and channels.
- **FR-14.02**: Messages in designated channels trigger agent processing.
- **FR-14.03**: Agent responses are posted back to the channel or as DMs.
- **FR-14.04**: Support for slash commands to interact with agents (e.g., `/ask`, `/status`, `/approve`).
- **FR-14.05**: Approval requests from agents can be surfaced as Discord interactive components (buttons).
- **FR-14.06**: Bot token and server config stored in environment/secrets, not in code.
- **FR-14.07**: DM security: pairing/allowlist model (reference OpenClaw's DM security patterns).

## Acceptance Criteria

- **AC-14.01**: Bot joins a server, receives a message, agent processes it, response appears in channel.
- **AC-14.02**: Slash command `/ask` sends a prompt to an agent and displays the response.
- **AC-14.03**: An approval request shows as a button; clicking approve/reject triggers the corresponding action.
- **AC-14.04**: Unapproved DMs are blocked or require pairing.

## QA Checklist

- [ ] **Unit Tests**: Message parsing, command handling, response formatting, security checks.
- [ ] **Integration Tests**: End-to-end Discord message → agent → response → Discord.
- [ ] **Human Walkthrough**: Interact with bot in Discord, use slash commands, trigger approval flow.
- [ ] **Constitution: Security (VI)**: Token in secrets. DMs secured. Input treated as untrusted.
- [ ] **Constitution: Serverless-First (I)**: Lambda behind API Gateway webhook (not a persistent bot process).

## Dependencies

- **Depends on**: REQ-01 (Lambda, API Gateway), REQ-05 (Workflow), REQ-09 (patterns from web chat)
- **Blocks**: REQ-17, REQ-18 (Slack and Teams follow the same pattern)
