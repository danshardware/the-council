# REQ-17: Slack Channel

## Overview
Slack bot integration for human-agent communication via Slack workspaces.

## Source
- [00_The Council.md](../00_The%20Council.md) → Communication Channels (Slack — eventually)

## Phase
Phase 3 — Future

## Functional Requirements

- **FR-17.01**: Slack bot (Bolt-style) connects via Socket Mode or webhooks.
- **FR-17.02**: Messages in designated channels trigger agent processing.
- **FR-17.03**: Agent responses posted back to channels or threads.
- **FR-17.04**: Slash commands for agent interaction.
- **FR-17.05**: Interactive components (buttons/modals) for approval workflows.
- **FR-17.06**: Follow the same channel adapter pattern as Discord (REQ-14).

## Acceptance Criteria

- **AC-17.01**: Bot responds to messages in a Slack channel.
- **AC-17.02**: Approval flow works via Slack interactive components.

## Dependencies

- **Depends on**: REQ-14 (Discord establishes the channel adapter pattern)
