# REQ-02: Core Agent Framework (includes LLM Integration)

## Overview
Implement the core agent runtime based on PocketFlow. Agents are defined declaratively via YAML, composed from nodes and flows, and can be created programmatically at runtime. This is the execution engine that all agent behaviors run on. Includes the LLM integration layer (formerly REQ-03): Conversation API bridge, model routing, and token budget tracking.

**Before implementation begins**, a design story (S00) works with a human to define use cases, schemas, and sample flows.

## Source
- [00_The Council.md](../00_The%20Council.md) → Agents: Functional Requirements (Modular agents), Technical Requirements (PocketFlow, Conversations API, cost-efficient LLM usage)

## Phase
Phase 1 — MVP (Critical)

## Functional Requirements

### Agent Framework
- **FR-02.01**: PocketFlow library integrated with typing issues resolved. Custom fork maintained in the project.
- **FR-02.02**: Agents can be defined via YAML files specifying: name, description, system prompts, tools, permissions, flows, and model configuration.
- **FR-02.03**: Agents can be created programmatically at runtime by other agents for specialized tasks.
- **FR-02.04**: Agent prompts can be loaded from an MCP Server.
- **FR-02.05**: Agents can have multiple sessions open simultaneously.
- **FR-02.06**: Every agent action is logged in a structured format to S3 JSONL (agent ID, session ID, action type, timestamp, inputs, outputs, token cost).
- **FR-02.07**: Base PocketFlow nodes created for: LLM call, tool invocation, human input, checkpoint, state checkpoint, and logging.
- **FR-02.08**: Base PocketFlow flows created for: Ralph loop, Chain of Thought.
- **FR-02.09**: Agent YAML schema is validated on load with clear error messages for invalid definitions.
- **FR-02.10**: Agent lifecycle: create → initialize → run sessions → teardown. Clean resource management.
- **FR-02.11**: Agents can checkpoint their state to S3 (serialize shared store under session ID) and resume from checkpoint.

### LLM Integration (merged from REQ-03)
- **FR-02.12**: Existing `Conversation` class from `conversation/conversation.py` integrated as the LLM interface for all agent nodes.
- **FR-02.13**: Model router selects LLM based on task type: expensive models for reasoning/planning, cheap models for extraction/classification/formatting/guardrails.
- **FR-02.14**: Model configuration is per-agent (in YAML) with system-wide defaults and per-node overrides.
- **FR-02.15**: Token usage tracked per-call, per-session, per-agent. Aggregated and available for cost reporting.
- **FR-02.16**: Budget guardrails: configurable per-session and per-agent token limits that halt execution when exceeded.
- **FR-02.17**: Tool use (function calling) flows through the Conversation API's existing tool mechanism.

### Human-in-the-Loop
- **FR-02.18**: Human input requests pause agent execution via SQS queue + S3 state checkpoint. Response triggers new Lambda invocation that resumes from checkpoint.

## Non-Functional Requirements

- **NFR-02.01**: Agent YAML loading and validation completes in under 500ms.
- **NFR-02.02**: Agent framework adds less than 10ms overhead per node execution (excluding LLM latency).
- **NFR-02.03**: Framework supports at least 50 concurrent agent sessions in a single Lambda invocation context.
- **NFR-02.04**: LLM wrapper adds less than 50ms overhead per call (excluding API latency).
- **NFR-02.05**: Token tracking is accurate to within 1% of Bedrock's reported usage.

## Acceptance Criteria

- **AC-02.01**: A YAML-defined agent loads, initializes, and executes a simple flow (input → LLM → output).
- **AC-02.02**: An agent created at runtime (no YAML) executes the same flow successfully.
- **AC-02.03**: Invalid YAML definitions produce clear validation errors without crashing.
- **AC-02.04**: Two sessions of the same agent run concurrently with isolated state.
- **AC-02.05**: All actions during a flow execution appear in the structured action log (S3 JSONL) with correct metadata.
- **AC-02.06**: The Ralph loop flow iterates on a simple task until completion or max iterations.
- **AC-02.07**: The Chain of Thought flow produces step-by-step reasoning logged at each step.
- **AC-02.08**: Agent prompts loaded from MCP Server are correctly injected into the agent's system prompt.
- **AC-02.09**: A reasoning task routes to an expensive model; a formatting task routes to a cheap model.
- **AC-02.10**: When a session exceeds its token budget, execution halts with a clear budget-exceeded error.
- **AC-02.11**: An agent with tool definitions can invoke tools via the LLM's function calling interface.
- **AC-02.12**: Agent state can be checkpointed to S3 and fully restored from checkpoint.
- **AC-02.13**: Human input request pauses via SQS, human responds, agent resumes from S3 checkpoint.

## QA Checklist

- [ ] **Unit Tests**: YAML parsing, schema validation, node execution, flow sequencing, action logging, model routing, token tracking, budget enforcement, state serialization.
- [ ] **Integration Tests**: Full agent lifecycle (YAML → load → session → execute flow → log → teardown). Full LLM round-trip (agent node → Conversation API → Bedrock → response).
- [ ] **Human Walkthrough**: Define a new agent via YAML, run it, inspect the action log, confirm each step is visible. Verify model routing and token tracking.
- [ ] **Constitution: Agent Modularity (II)**: Agents are independently testable. No cross-agent dependencies at framework level.
- [ ] **Constitution: Observability (V)**: Every node execution logged with full metadata.
- [ ] **Constitution: Simplicity (VII)**: No unnecessary abstractions. PocketFlow's 100-line core is extended, not replaced.
- [ ] **Constitution: Test-First (III)**: Tests written for each node type and flow pattern before implementation.
- [ ] **Constitution: Cost-Conscious (IV)**: Cheap models used for routine tasks. Expensive models only when justified.
- [ ] **Coding: Type Hints**: All framework classes and functions have complete type annotations.
- [ ] **Coding: Docstrings**: All public classes and methods have PEP 257 docstrings.

## Dependencies

- **Depends on**: REQ-01 (Shared Resources — S3 bucket)
- **Blocks**: REQ-04, REQ-05, REQ-08, REQ-11, REQ-12, REQ-13
