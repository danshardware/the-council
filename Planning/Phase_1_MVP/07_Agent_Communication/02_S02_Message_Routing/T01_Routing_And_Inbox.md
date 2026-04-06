# Task: Message Routing and Agent Inbox Queue

## Parent
- **Requirement**: REQ-07 Agent Communication
- **Story**: S02 Message Routing

## Description
Implement the routing layer: when a message is posted to a room, queue it to all subscribed agents' inboxes. New inbox messages trigger agent processing.

## Acceptance Criteria
- [ ] **AC-01**: Posting to a room fans out the message to all subscribed agents' inboxes.
- [ ] **AC-02**: Agent inbox implemented via SQS queue per agent (or a shared queue with agent_id routing).
- [ ] **AC-03**: New inbox messages trigger Lambda invocations via SQS.
- [ ] **AC-04**: Messages are marked as processed after agent handles them.
- [ ] **AC-05**: At-least-once delivery: agent will see the message even if Lambda cold-starts.
- [ ] **AC-06**: Resource references in messages (S3 keys, conversation IDs) are resolvable by the receiving agent.

## QA Checklist
- [ ] pytest tests: fan-out logic, SQS delivery, trigger mechanism, processed marking, resource resolution.
- [ ] **Constitution: Serverless-First (I)**: SQS for triggering. No persistent queue workers.
- [ ] **Constitution: Security (VI)**: Messages from other agents treated as potentially untrusted.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
