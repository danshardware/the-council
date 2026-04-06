# Task: Tool Invocation Node

## Parent
- **Requirement**: REQ-02 Core Agent Framework
- **Story**: S05 Base Nodes

## Description
PocketFlow node that invokes registered tools by name with validated inputs. Captures output and handles errors.

## Acceptance Criteria
- [ ] **AC-01**: `ToolInvocationNode` receives tool name and arguments from shared store, invokes the tool, and stores the result.
- [ ] **AC-02**: Unknown tool names produce a clear error without crashing.
- [ ] **AC-03**: Tool execution timeout is enforced.
- [ ] **AC-04**: Tool invocation is logged with tool name, inputs, outputs, and duration.

## QA Checklist
- [ ] pytest tests: successful invocation, unknown tool, timeout, error handling.
- [ ] **Constitution: Observability (V)**: Tool calls logged.
- [ ] **Constitution: Security (VI)**: Tool permissions checked before invocation.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
