# REQ-10: Activity Dashboard UI

## Overview
Web UI panel that displays agent activity history, allows inspection of workflows, and provides visibility into what agents are doing and have done.

## Source
- [00_The Council.md](../00_The%20Council.md) → UI/UX (Show history of agent activity)

## Phase
Phase 1 — MVP (Critical)

## Functional Requirements

- **FR-10.01**: Web UI panel showing agent activity organized by agent and session.
- **FR-10.02**: Activity timeline for each session showing all actions in chronological order.
- **FR-10.03**: Each action type has a distinct icon/emoji: thinking 🧠, tool call 🔧, guardrail 🛡️, checkpoint ⏸️, communication 💬, error ❌, completion ✅.
- **FR-10.04**: Actions have configurable default expand/collapse state — high-level summary shown by default, full detail on expand.
- **FR-10.05**: Users can follow conversation chains that spawn sub-agents — clicking into a sub-agent action navigates to that sub-agent's session timeline.
- **FR-10.06**: Each session displays a summary table of: all resources touched (files, memories, messages) and all actions taken.
- **FR-10.07**: Filter and search across activity: by agent, by session, by action type, by time range, by resource.
- **FR-10.08**: Polling-based updates — active sessions refresh via periodic GET calls. WebSocket can be added in a later iteration.
- **FR-10.09**: Reference GitHub Copilot's agent activity display and OpenClaw's session UI for UX patterns.

## Non-Functional Requirements

- **NFR-10.01**: Dashboard loads last 100 actions in under 2 seconds.
- **NFR-10.02**: Polling updates appear within 5 seconds of action completion.
- **NFR-10.03**: Dashboard is responsive and functional on desktop browsers (mobile not required for MVP).

## Acceptance Criteria

- **AC-10.01**: Opening the dashboard shows a list of agents and their recent sessions.
- **AC-10.02**: Clicking a session shows its activity timeline with icons for each action type.
- **AC-10.03**: Expanding a "tool call" action shows the tool name, inputs, outputs, and duration.
- **AC-10.04**: A session that spawned a sub-agent shows a link to the sub-agent's timeline.
- **AC-10.05**: The session summary table lists all files touched and actions taken.
- **AC-10.06**: Filtering by action type (e.g., show only errors) works correctly.
- **AC-10.07**: While an agent is actively running, new actions appear in the timeline on polling refresh.

## QA Checklist

- [ ] **Unit Tests**: API endpoints for fetching activity data. Filtering logic. Data formatting.
- [ ] **Integration Tests**: Agent runs a workflow → dashboard displays all actions correctly.
- [ ] **Human Walkthrough**: Run an agent doing a multi-step task. Watch the dashboard in real time. Inspect each action type. Follow a sub-agent chain.
- [ ] **Constitution: Observability (V)**: Dashboard is the primary observability surface. All logged actions are visible.
- [ ] **Constitution: Serverless-First (I)**: Static UI on S3. API via API Gateway + Lambda. Polling for updates.
- [ ] **Constitution: Simplicity (VII)**: Clean, functional UI. No unnecessary features beyond inspection and filtering.
- [ ] **UX Reference**: Compare against GitHub Copilot agent activity and OpenClaw Control UI.

## Dependencies

- **Depends on**: REQ-01 (API Gateway, S3, Lambda), REQ-05 (Action logs from workflow engine)
- **Blocks**: REQ-16 (Config editing UI extends this surface)
