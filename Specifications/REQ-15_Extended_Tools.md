# REQ-15: Extended Tools Suite

## Overview
Additional tools beyond the core set: GitKraken integration, Kanban work board, web browser control, approval workflows, and coding tools.

## Source
- [00_The Council.md](../00_The%20Council.md) → Tools (Git Kraken, Kanban, Web, Get approvals, Coding)

## Phase
Phase 2 — Important

## Functional Requirements

- **FR-15.01**: **GitKraken/Git**: Clone, branch, commit, push, pull, diff, blame operations on CodeCommit repos.
- **FR-15.02**: **Kanban Board**: Work board with swimlanes, item dependency tracking, and agent/human assignment. Stored in DynamoDB. Basic CRUD + move/assign operations.
- **FR-15.03**: **Web Browser**: Headless browser (or connect to debug port) for browsing, downloading, searching. Supports page navigation, content extraction, form filling, and screenshot.
- **FR-15.04**: **Get Approvals**: Formal approval workflow tool. Creates an approval request, routes to designated approvers, collects responses, and returns result.
- **FR-15.05**: **Coding Tools**: Code generation, linting, formatting, and test execution tools. Operate within agent workspaces.
- **FR-15.06**: All extended tools registered as `BedrockTool` instances and logged per the core tools pattern (REQ-08).
- **FR-15.07**: Reuse existing open-source tools where possible (referenced in project doc: "try to get as many from existing code bases as possible").

## Acceptance Criteria

- **AC-15.01**: An agent clones a CodeCommit repo, creates a branch, makes a commit, and pushes.
- **AC-15.02**: An agent creates a Kanban item, assigns it, moves it between swimlanes, and marks it complete.
- **AC-15.03**: An agent navigates to a webpage, extracts content, and returns structured data.
- **AC-15.04**: An agent requests board approval; approval is granted; agent proceeds.
- **AC-15.05**: An agent generates code, runs tests, and reports results.

## QA Checklist

- [ ] **Unit Tests**: Each tool function tested. Git operations mocked at CodeCommit level.
- [ ] **Integration Tests**: Multi-tool workflow (e.g., clone repo → write code → commit → push).
- [ ] **Human Walkthrough**: Use each tool through an agent conversation and verify results.
- [ ] **Constitution: Security (VI)**: Git credentials via IAM. Browser in sandbox. No credential exposure.
- [ ] **Constitution: Human-in-the-Loop (VIII)**: Approval tool correctly gates irreversible actions.

## Dependencies

- **Depends on**: REQ-01 (CodeCommit, DynamoDB), REQ-02 (Agent Framework), REQ-08 (Core Tools pattern)
- **Blocks**: None
