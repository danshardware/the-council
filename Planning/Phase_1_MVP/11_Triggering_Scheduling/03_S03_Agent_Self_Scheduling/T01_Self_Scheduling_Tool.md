# Task: Agent Self-Scheduling Tool

## Parent
- **Requirement**: REQ-11 Triggering & Scheduling
- **Story**: S03 Agent Self-Scheduling

## Description
A tool that agents can invoke to schedule themselves (or other agents) for future execution. Uses EventBridge Scheduler to create one-time or recurring triggers. This enables agents to set reminders, defer work, or create follow-up tasks.

## Acceptance Criteria
- [ ] **AC-01**: `schedule_self(cron_or_datetime, prompt, recurring=False)` tool creates an EventBridge schedule targeting the calling agent.
- [ ] **AC-02**: `schedule_agent(agent_id, cron_or_datetime, prompt, recurring=False)` schedules a different agent.
- [ ] **AC-03**: One-time schedules auto-delete after execution.
- [ ] **AC-04**: Recurring schedules support cron expressions.
- [ ] **AC-05**: Agent can list and cancel its own scheduled items.
- [ ] **AC-06**: All schedule operations logged in action logs.
- [ ] **AC-07**: Tools registered as `BedrockTool` instances.

## QA Checklist
- [ ] pytest tests: schedule creation, cron parsing, cancellation, listing, auto-cleanup.
- [ ] **Constitution: Serverless-First (I)**: EventBridge Scheduler, no cron daemons.
- [ ] **Constitution: Security (VI)**: Agents can only cancel their own schedules.
- [ ] **Constitution: Observability (V)**: All schedule ops logged.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
