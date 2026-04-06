# Task: Human Input, AgentChat, and Session TODO Tools

## Parent
- **Requirement**: REQ-08 Core Tools
- **Story**: S03 Human Interaction Tools

## Description
Three tools: Get Human Input (pause and request human input), AgentChat (message another agent), and Session TODO (track tasks within a session).

## Acceptance Criteria
- [ ] **AC-01**: `get_human_input(prompt, context)` pauses execution, stores the request, and resumes when input arrives.
- [ ] **AC-02**: `agent_chat(target_agent, message, await_reply)` sends a message and optionally waits for response.
- [ ] **AC-03**: `session_todo_add(title)`, `session_todo_update(id, status)`, `session_todo_list()` manage a task list.
- [ ] **AC-04**: TODO statuses: not-started, in-progress, completed.
- [ ] **AC-05**: All tools registered via `@bedrock_tool` and logged.

## QA Checklist
- [ ] pytest tests: pause/resume for human input, agent chat routing, TODO CRUD, status transitions.
- [ ] **Constitution: Human-in-the-Loop (VIII)**: Human input tool is the gateway for approval.
- [ ] **Constitution: Observability (V)**: All interactions logged.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
