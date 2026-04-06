# REQ-05: Agent Workflow Engine

## Overview
Implement the standard agent workflow cycle: Thinking → Guardrails → Checkpoint → Action → Guardrails → Decide Next Step. This is the core execution loop that all long-term agents follow.

## Source
- [00_The Council.md](../00_The%20Council.md) → Agents: Functional Requirements (Long Term Agents workflow)

## Phase
Phase 1 — MVP (Critical)

## Functional Requirements

- **FR-05.01**: Standard workflow cycle implemented as a PocketFlow flow: Think → Pre-Action Guardrails → Checkpoint → Action → Post-Action Guardrails → Decide.
- **FR-05.02**: **Thinking Phase**: Agent reasons about the current state, available information, and next best action. Uses chain-of-thought when beneficial.
- **FR-05.03**: **Pre-Action Guardrails**: Prompt injection check and goal drift check run before any action.
- **FR-05.04**: **Checkpoint Phase**: Before any irreversible action, the system pauses and (if configured) requests human approval. Reversible actions proceed automatically.
- **FR-05.05**: **Action Phase**: Agent executes one of: tool call, communicate with another agent, request user feedback, or stop.
- **FR-05.06**: **Post-Action Guardrails**: Validate the action result. Check for errors, unexpected outputs, or security concerns.
- **FR-05.07**: **Decide Phase**: Agent evaluates the result and decides whether to continue the loop, start a new task, or terminate the session.
- **FR-05.08**: The workflow cycle is configurable — agents can skip optional phases (e.g., skip checkpoint for low-risk actions).
- **FR-05.09**: Each phase transition is logged as a distinct action in the action log.
- **FR-05.10**: Maximum iteration limit prevents infinite loops. Configurable per-agent with a system default.

## Non-Functional Requirements

- **NFR-05.01**: A single workflow cycle (excluding LLM latency and tool execution) completes in under 200ms of framework overhead.
- **NFR-05.02**: Workflow state is serializable for Lambda cold-start recovery.

## Acceptance Criteria

- **AC-05.01**: An agent executes a complete workflow cycle (all phases) and the action log shows each phase.
- **AC-05.02**: A dangerous action (e.g., file deletion) triggers the checkpoint phase and pauses for human approval.
- **AC-05.03**: A safe action (e.g., reading a file) skips the checkpoint and proceeds automatically.
- **AC-05.04**: An agent that drifts from its goal is flagged by pre-action guardrails.
- **AC-05.05**: An agent that exceeds the maximum iteration limit stops with a clear max-iterations-reached status.
- **AC-05.06**: The decide phase correctly routes to: continue loop, new task, or terminate.
- **AC-05.07**: Workflow configuration in YAML correctly enables/disables optional phases.

## QA Checklist

- [ ] **Unit Tests**: Each phase tested independently. Phase transitions tested. Configuration parsing tested.
- [ ] **Integration Tests**: Full multi-cycle workflow with tool calls, guardrails, and checkpoints.
- [ ] **Human Walkthrough**: Observe an agent running a multi-step task. Verify checkpoint pauses. Confirm logs show every phase.
- [ ] **Constitution: Human-in-the-Loop (VIII)**: Irreversible actions checkpoint correctly.
- [ ] **Constitution: Observability (V)**: Every phase transition logged.
- [ ] **Constitution: Security (VI)**: Guardrails run on every cycle.
- [ ] **Constitution: Simplicity (VII)**: Workflow is a simple state machine, not over-engineered.

## Dependencies

- **Depends on**: REQ-02 (PocketFlow, LLM), REQ-04 (Guardrails)
- **Blocks**: REQ-06, REQ-07, REQ-12
