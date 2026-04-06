# REQ-08: Core Tools

## Overview
The essential tool set that agents need to perform basic operations: file manipulation, command execution, sub-agent spawning, human interaction, and task tracking.

## Source
- [00_The Council.md](../00_The%20Council.md) → Tools (basic file tools, execute, run sub agent, get human input, session TODO)

## Phase
Phase 1 — MVP (Critical)

## Functional Requirements

- **FR-08.01**: **File Search**: Search for files in S3 by name pattern, path prefix, or content keywords.
- **FR-08.02**: **File Read**: Read file contents from S3. Support text files and JSON. Return content or a presigned URL for large files.
- **FR-08.03**: **File Edit**: Create, update, and delete files in S3. Edits are versioned (S3 versioning).
- **FR-08.04**: **Execute**: Run commands in a restricted sandbox. Configurable allowlist/denylist of commands. Timeout enforcement. Output capture.
- **FR-08.05**: **Run Sub-Agent**: Spawn a new agent (from YAML or programmatic definition) to handle a scoped sub-task. Await result or fire-and-forget.
- **FR-08.06**: **AgentChat**: Send a message to another agent and optionally wait for a response. Builds on the communication system (REQ-07).
- **FR-08.07**: **Get Human Input**: Pause agent execution and request input from a human via the configured channel. Resume when input received.
- **FR-08.08**: **Session TODO**: Track a list of tasks within an agent session. Add, update status (not-started / in-progress / completed), and list.
- **FR-08.09**: All tools are registered as `BedrockTool` instances via the existing `@bedrock_tool` decorator for LLM function calling.
- **FR-08.10**: All tool invocations are logged with: tool name, input parameters, output, duration, and any errors.
- **FR-08.11**: Tools operate within agent permissions — an agent can only access files/commands its configuration allows.

## Non-Functional Requirements

- **NFR-08.01**: File operations complete in under 2 seconds for files under 1MB.
- **NFR-08.02**: Command execution has a configurable timeout (default 30 seconds, max 300 seconds).
- **NFR-08.03**: Sub-agent spawning completes initialization in under 5 seconds.

## Acceptance Criteria

- **AC-08.01**: An agent searches for files matching a pattern and gets correct results.
- **AC-08.02**: An agent reads a text file from S3 and gets the correct content.
- **AC-08.03**: An agent creates a file, edits it, and the versions are preserved in S3.
- **AC-08.04**: An agent executes an allowed command and receives stdout/stderr output.
- **AC-08.05**: An agent executes a denied command and gets a permission-denied error.
- **AC-08.06**: An agent spawns a sub-agent, the sub-agent completes its task, and the result is returned.
- **AC-08.07**: An agent requests human input, the system pauses, human provides input, agent resumes.
- **AC-08.08**: Session TODO operations (add, update, list) work correctly through agent tool calls.
- **AC-08.09**: An agent without file permissions cannot access file tools.
- **AC-08.10**: All tool calls appear in the action log.

## QA Checklist

- [ ] **Unit Tests**: Each tool function tested with valid and invalid inputs. Permission enforcement tested.
- [ ] **Integration Tests**: Agent workflow using multiple tools in sequence (read file → process → write result).
- [ ] **Human Walkthrough**: Run an agent that uses each tool type. Verify outputs and logs.
- [ ] **Constitution: Security (VI)**: Execute tool has allowlist. Permission boundaries enforced. No arbitrary command execution.
- [ ] **Constitution: Observability (V)**: All tool calls logged with full I/O.
- [ ] **Constitution: Human-in-the-Loop (VIII)**: Get Human Input tool works correctly for approval flows.
- [ ] **Constitution: Simplicity (VII)**: Tools are thin wrappers around AWS SDK calls. No unnecessary abstraction layers.

## Dependencies

- **Depends on**: REQ-01 (S3, Lambda), REQ-02 (PocketFlow, BedrockTool)
- **Blocks**: REQ-15 (Extended tools build on this foundation)
