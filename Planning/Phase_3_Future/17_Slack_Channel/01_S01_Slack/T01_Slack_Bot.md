# Task: Slack Bot Integration

## Parent
- **Requirement**: REQ-17 Slack Channel
- **Story**: S01 Slack Integration

## Description
Build a Slack bot that connects to The Council via API Gateway. Slash commands, mentions, and DMs trigger agent interactions. Messages relayed through the channel abstraction layer.

## Acceptance Criteria
- [ ] **AC-01**: Slack app registered with Events API subscription (message, mention, slash commands).
- [ ] **AC-02**: Lambda handler receives Slack events, maps to channel-agnostic message format.
- [ ] **AC-03**: Agent responses posted back to the originating Slack channel/thread.
- [ ] **AC-04**: Rich formatting: code blocks, attachments, thread replies.
- [ ] **AC-05**: Slash commands: `/council ask <prompt>`, `/council status`, `/council agents`.

## QA Checklist
- [ ] pytest tests: event parsing, message formatting, response posting.
- [ ] **Constitution: Security (VI)**: Slack signing secret verified on every request.
- [ ] **Constitution: Observability (V)**: All Slack events logged.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
