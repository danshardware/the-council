# Task: Human Input and Checkpoint Nodes

## Parent
- **Requirement**: REQ-02 Core Agent Framework
- **Story**: S05 Base Nodes

## Description
PocketFlow nodes for human interaction: `HumanInputNode` pauses execution to request input from a human, `CheckpointNode` pauses for approval before destructive actions.

**Pause/Resume Design**: When pausing, the node serializes the agent's full state (via `StateCheckpointNode` — see T04) to S3, then pushes a request message to an SQS queue. The Lambda returns. When the human responds (via chat UI or API), a message is placed on a response SQS queue, which triggers a new Lambda invocation that loads the checkpoint from S3 and resumes the flow from where it paused.

## Acceptance Criteria
- [ ] **AC-01**: `HumanInputNode` checkpoints agent state to S3, pushes a request to SQS, and terminates the Lambda.
- [ ] **AC-02**: When human input arrives (via response SQS queue), a new Lambda loads the checkpoint and resumes flow with the input in shared store.
- [ ] **AC-03**: `CheckpointNode` evaluates whether the pending action is destructive. If yes, pauses for approval via SQS. If no, continues.
- [ ] **AC-04**: Approval/rejection is logged with the approver's identity.
- [ ] **AC-05**: Request messages include: session_id, agent_id, prompt, context, checkpoint S3 key.
- [ ] **AC-06**: Timeout on human response is configurable. Default: 24 hours. Expired requests are logged and agent notified.

## QA Checklist
- [ ] pytest tests: checkpoint + SQS push, resume from checkpoint, destructive action detection, approval logging, timeout.
- [ ] **Constitution: Human-in-the-Loop (VIII)**: Destructive actions always checkpoint.
- [ ] **Constitution: Observability (V)**: Checkpoint decisions and SQS messages logged.
- [ ] **Constitution: Serverless-First (I)**: SQS + Lambda. No polling loops or persistent processes.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
