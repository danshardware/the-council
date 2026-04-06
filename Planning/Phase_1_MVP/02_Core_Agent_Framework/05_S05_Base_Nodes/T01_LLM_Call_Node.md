# Task: LLM Call Node

## Parent
- **Requirement**: REQ-02 Core Agent Framework
- **Story**: S05 Base Nodes

## Description
PocketFlow node that wraps the Conversation API to make LLM calls. Handles prompt construction, tool configuration, response parsing, and token tracking.

## Acceptance Criteria
- [ ] **AC-01**: `LLMCallNode` extends PocketFlow `Node`. Prep loads prompt and tools. Exec calls Conversation API. Post parses response.
- [ ] **AC-02**: Token usage from the call is tracked and emitted as shared store data.
- [ ] **AC-03**: Tool-use responses are correctly parsed and routed.
- [ ] **AC-04**: Retry logic handles transient Bedrock errors (throttling, timeout).
- [ ] **AC-05**: Each call is logged via the action logging system.

## QA Checklist
- [ ] pytest tests: prompt construction, response parsing, token tracking, retry behavior, error handling.
- [ ] **Constitution: Cost-Conscious (IV)**: Token usage emitted for tracking.
- [ ] **Constitution: Observability (V)**: Every LLM call logged.
- [ ] **Coding: Type Hints**: Node input/output types fully annotated.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
