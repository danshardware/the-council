# Task: Message Board Rooms and Messages

## Parent
- **Requirement**: REQ-07 Agent Communication
- **Story**: S01 Message Board

## Description
Implement the message board system: room CRUD, message posting, room subscriptions, and message storage in S3.

## Acceptance Criteria
- [ ] **AC-01**: `MessageBoard` class supports room creation, listing, joining, and leaving.
- [ ] **AC-02**: Messages posted to rooms with: sender_id, room_id, content, resource_refs[], conversation_id (optional), timestamp, message_id.
- [ ] **AC-03**: Room history queryable by listing S3 objects under `messages/{room_id}/` prefix (sorted by timestamp key).
- [ ] **AC-04**: Default rooms (`#general`, `#alerts`, `#approvals`) created on system initialization.
- [ ] **AC-05**: Direct messages between agents stored under a private room prefix (two subscribers).
- [ ] **AC-06**: Room configs stored in S3 `config/rooms/{room_id}.json`.

## QA Checklist
- [ ] pytest tests: room CRUD, message posting, history queries, DM creation, default rooms.
- [ ] **Constitution: Serverless-First (I)**: S3 storage only.
- [ ] **Constitution: Observability (V)**: Message routing logged.
- [ ] **Coding: Type Hints**: Message and Room dataclasses fully typed.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
