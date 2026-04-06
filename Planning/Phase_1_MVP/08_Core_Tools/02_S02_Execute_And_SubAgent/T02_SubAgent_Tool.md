# Task: Run Sub-Agent Tool

## Parent
- **Requirement**: REQ-08 Core Tools
- **Story**: S02 Execute and SubAgent

## Description
Tool that spawns a new agent to handle a scoped sub-task. Supports await (synchronous) and fire-and-forget modes.

## Acceptance Criteria
- [ ] **AC-01**: `run_sub_agent(definition, task, mode)` creates and runs a sub-agent.
- [ ] **AC-02**: `mode="await"`: blocks until sub-agent completes, returns result.
- [ ] **AC-03**: `mode="async"`: fires sub-agent and returns immediately with a session ID for later polling.
- [ ] **AC-04**: Sub-agent's actions appear in the parent's activity log as a nested entry.
- [ ] **AC-05**: Sub-agent inherits parent's budget constraints (or has its own, whichever is smaller).

## QA Checklist
- [ ] pytest tests: sync mode, async mode, nested logging, budget inheritance.
- [ ] **Constitution: Agent Modularity (II)**: Sub-agents are full agents with isolated state.
- [ ] **Constitution: Observability (V)**: Parent ↔ child relationship visible in logs.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
