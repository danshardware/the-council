# REQ-11: Triggering & Scheduling

## Overview
System for triggering agent actions via schedules, AWS events, and chat inputs. Enables autonomous agent operations on timers and reactive behavior from infrastructure events.

## Source
- [00_The Council.md](../00_The%20Council.md) → Triggering Actions

## Phase
Phase 1 — MVP (Critical)

## Functional Requirements

- **FR-11.01**: **Scheduled Actions**: Cron-style schedules that trigger either a program (Lambda) or a prompt sent to a specific agent.
- **FR-11.02**: Schedules defined in S3 configuration (`config/schedules/` as JSON). CRUD operations for schedule management.
- **FR-11.03**: **AWS Event Mapping**: CloudWatch Events / EventBridge rules can be mapped to agent prompts. E.g., an S3 upload triggers an agent to process the file.
- **FR-11.04**: **Chat Triggers**: Incoming chat messages (from REQ-09 web chat) trigger the appropriate agent.
- **FR-11.05**: Trigger execution is logged: trigger type, timestamp, target agent, input payload, and result status.
- **FR-11.06**: Triggers support conditional execution — e.g., only trigger during business hours, or only if a condition is met.
- **FR-11.07**: Failed trigger executions retry with configurable backoff (1, 2, 3 attempts).
- **FR-11.08**: **Agent Self-Scheduling**: Agents can schedule themselves or other agents for future execution via a `schedule_self` / `schedule_agent` tool. One-time and recurring schedules supported.

## Non-Functional Requirements

- **NFR-11.01**: Scheduled triggers fire within 60 seconds of their scheduled time.
- **NFR-11.02**: Event-driven triggers fire within 5 seconds of the event.
- **NFR-11.03**: All triggers are serverless (EventBridge rules + Lambda targets).

## Acceptance Criteria

- **AC-11.01**: A scheduled action fires at the configured time and the target agent receives the prompt.
- **AC-11.02**: An EventBridge rule for S3 object creation triggers an agent with the file details.
- **AC-11.03**: A chat message triggers the appropriate agent and the response flows back to the chat.
- **AC-11.04**: A failed trigger retries up to the configured limit, then logs the failure.
- **AC-11.05**: Trigger execution history is visible in the activity dashboard.
- **AC-11.06**: Schedules can be created, updated, and deleted via configuration.

## QA Checklist

- [ ] **Unit Tests**: Schedule parsing, event mapping, trigger routing, retry logic, conditional execution.
- [ ] **Integration Tests**: End-to-end: schedule fires → agent invoked → response generated → logged.
- [ ] **Human Walkthrough**: Create a schedule, wait for it to fire, verify agent ran and logged the action.
- [ ] **Constitution: Serverless-First (I)**: EventBridge + Lambda. No cron daemons or persistent schedulers.
- [ ] **Constitution: Observability (V)**: All trigger executions logged with full context.
- [ ] **Constitution: Security (VI)**: Event payloads treated as untrusted input, run through guardrails.
- [ ] **Constitution: Simplicity (VII)**: Use native AWS scheduling (EventBridge), don't build a custom scheduler.

## Dependencies

- **Depends on**: REQ-01 (EventBridge, Lambda), REQ-02 (Agent Framework)
- **Blocks**: None (this is a leaf requirement)
