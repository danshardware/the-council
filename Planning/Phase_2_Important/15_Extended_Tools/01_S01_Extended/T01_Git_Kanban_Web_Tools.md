# Task: Git, Kanban, and Web Browser Tools

## Parent
- **Requirement**: REQ-15 Extended Tools Suite
- **Story**: S01 Extended Tools

## Description
Implement extended tools: Git operations (CodeCommit), Kanban work board (DynamoDB), and headless web browser control.

## Acceptance Criteria
- [ ] **AC-01**: Git tools: `git_clone`, `git_branch`, `git_commit`, `git_push`, `git_diff` — operate on CodeCommit repos.
- [ ] **AC-02**: Kanban tools: `kanban_create_item`, `kanban_move`, `kanban_assign`, `kanban_list` with swimlanes and dependencies.
- [ ] **AC-03**: Web tools: `web_browse(url)`, `web_search(query)`, `web_extract(url, selector)`, `web_screenshot(url)`.
- [ ] **AC-04**: All tools registered as BedrockTool instances and logged.
- [ ] **AC-05**: Git credentials via IAM (CodeCommit). Web browser sandboxed.

## QA Checklist
- [ ] pytest tests: each tool function with valid/invalid inputs.
- [ ] **Constitution: Security (VI)**: Git via IAM. Browser sandboxed. No credential exposure.
- [ ] **Constitution: Observability (V)**: All tool calls logged.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
