# REQ-18: Teams Channel

## Overview
Microsoft Teams bot integration for human-agent communication.

## Source
- [00_The Council.md](../00_The%20Council.md) → Communication Channels (Teams — eventually)

## Phase
Phase 3 — Future

## Functional Requirements

- **FR-18.01**: Teams bot via Bot Framework SDK.
- **FR-18.02**: Messages in designated channels/chats trigger agent processing.
- **FR-18.03**: Agent responses posted back. Adaptive cards for rich interactions.
- **FR-18.04**: Follow the same channel adapter pattern as Discord (REQ-14).

## Acceptance Criteria

- **AC-18.01**: Bot responds to messages in a Teams channel.
- **AC-18.02**: Approval flow works via Teams adaptive cards.

## Dependencies

- **Depends on**: REQ-14 (Discord establishes the channel adapter pattern)
