# REQ-07: Agent Communication

## Overview
A message board system with rooms and direct messaging that enables agents to communicate asynchronously. Messages reference internal resources and trigger processing queues.

## Source
- [00_The Council.md](../00_The%20Council.md) → Agents: Functional Requirements (Agent communication)

## Phase
Phase 1 — MVP (Critical)

## Functional Requirements

- **FR-07.01**: **Message Board** with rooms. Rooms can be created for general use or on-the-fly for specific purposes.
- **FR-07.02**: Posting a message to a room queues that message to every agent subscribed to the room.
- **FR-07.03**: **Direct Messages**: Agent-to-agent direct messages are supported.
- **FR-07.04**: Messages can reference internal resources: files (S3 keys), repositories (CodeCommit refs), conversation UUIDs, memory entries.
- **FR-07.05**: Messages without a conversation ID are treated as standalone communications about a topic.
- **FR-07.06**: Message format: sender_agent_id, target (room or agent), content, resource_references[], conversation_id (optional), timestamp, message_id.
- **FR-07.07**: Messages stored in S3 under `messages/{room_id}/` as JSON objects. Room membership stored in S3 `config/rooms/`.
- **FR-07.08**: Each agent has an inbox queue. New messages trigger the agent's processing (via Lambda invocation or SQS).
- **FR-07.09**: Room operations: create, list, join, leave, post, read history.
- **FR-07.10**: Default rooms created on system init: `#general`, `#alerts`, `#approvals`.

## Non-Functional Requirements

- **NFR-07.01**: Message delivery latency under 500ms (from post to queue appearance).
- **NFR-07.02**: Message board supports 1000+ messages per room without query degradation.
- **NFR-07.03**: No message loss — at-least-once delivery guaranteed.

## Acceptance Criteria

- **AC-07.01**: Agent A posts a message to `#general`. Agent B, subscribed to `#general`, receives it in their queue.
- **AC-07.02**: Agent A sends a direct message to Agent B. Only Agent B receives it.
- **AC-07.03**: A message referencing an S3 file includes the resource reference and the receiving agent can resolve it.
- **AC-07.04**: Creating a new room and subscribing agents to it works. Messages flow correctly.
- **AC-07.05**: Room history is queryable with pagination.
- **AC-07.06**: A message without a conversation_id is stored and retrievable as a standalone message.
- **AC-07.07**: Default rooms exist after system initialization.

## QA Checklist

- [ ] **Unit Tests**: Message creation, room CRUD, subscription management, queue operations, resource reference resolution.
- [ ] **Integration Tests**: Multi-agent communication flow: post → queue → receive → process.
- [ ] **Human Walkthrough**: Create room, post messages from two agents, verify both receive each other's messages, inspect resource references.
- [ ] **Constitution: Serverless-First (I)**: S3 for storage, SQS or Lambda for queuing.
- [ ] **Constitution: Observability (V)**: All messages logged with routing metadata.
- [ ] **Constitution: Security (VI)**: Messages treated as potentially untrusted — guardrails can scan them.
- [ ] **Constitution: Simplicity (VII)**: Simple pub/sub model. No complex event bus.

## Dependencies

- **Depends on**: REQ-01 (S3, SQS/Lambda), REQ-05 (Agents need workflow to process messages)
- **Blocks**: REQ-12 (Long-term agents communicate), REQ-13 (Short-term agents receive assignments)
