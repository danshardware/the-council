# REQ-04: Guardrail Blocks

## Overview
PocketFlow nodes that provide safety, quality, and alignment checks. These blocks are inserted into agent workflows to detect prompt injection, verify goal alignment, extract structured facts, and extract memory-worthy information.

## Source
- [00_The Council.md](../00_The%20Council.md) → Technical Requirements (PocketFlow blocks for critical functions)

## Phase
Phase 1 — MVP (Critical)

## Functional Requirements

- **FR-04.01**: **Prompt Injection Detection Block**: Analyzes incoming messages for prompt injection attempts or non-sequitur content. Returns a risk score and classification (safe / suspicious / blocked). Supports pluggable classifiers: LLM-based (cheap Bedrock model) and local classifiers (e.g., LangChain-based models).
- **FR-04.02**: **Goal Drift Detection Block**: Compares current agent state against its assigned goals/task. Flags when the agent has strayed from objectives. Uses a cheap model.
- **FR-04.03**: **Fact Extraction Block**: Extracts structured facts (entities, relationships, data points) from text. Returns structured JSON. Uses a cheap model.
- **FR-04.04**: **Memory Extraction Block**: Analyzes conversations/actions and identifies information worth storing in agent memory. Returns candidate memory entries with keywords and context. Uses a cheap model.
- **FR-04.05**: All guardrail blocks are composable PocketFlow nodes that can be inserted at any point in a flow.
- **FR-04.06**: Guardrail blocks log their decisions with reasoning for auditability.
- **FR-04.07**: Blocked content surfaces a clear explanation to the calling agent/user — no silent drops.

## Non-Functional Requirements

- **NFR-04.01**: Guardrail checks complete in under 2 seconds (including LLM call).
- **NFR-04.02**: Prompt injection detection has a false positive rate below 5% on standard test sets.

## Acceptance Criteria

- **AC-04.01**: A message containing a known prompt injection pattern is detected and blocked.
- **AC-04.02**: A benign message passes the injection check without false positive.
- **AC-04.03**: An agent given a research task that starts discussing unrelated topics triggers the goal drift detector.
- **AC-04.04**: Given a paragraph of text, the fact extraction block returns structured JSON with entities and relationships.
- **AC-04.05**: Given a multi-turn conversation, the memory extraction block identifies at least one memory-worthy item with keywords.
- **AC-04.06**: All guardrail decisions appear in the action log with reasoning.
- **AC-04.07**: Guardrail blocks use cheap models (not premium reasoning models).

## QA Checklist

- [ ] **Unit Tests**: Each block tested with known-good and known-bad inputs. Structured output schema validated.
- [ ] **Integration Tests**: Guardrail blocks wired into an agent flow correctly halt or pass execution.
- [ ] **Human Walkthrough**: Send adversarial messages to an agent, verify they are caught. Send normal messages, verify no false positives. Inspect logs.
- [ ] **Constitution: Security (VI)**: Prompt injection detection runs on all external input.
- [ ] **Constitution: Cost-Conscious (IV)**: All guardrails use cheapest viable model.
- [ ] **Constitution: Observability (V)**: Each guardrail decision logged with full reasoning.
- [ ] **Constitution: Test-First (III)**: Test cases (including adversarial) written before implementation.

## Dependencies

- **Depends on**: REQ-02 (PocketFlow nodes, LLM Integration)
- **Blocks**: REQ-05 (Workflow Engine uses guardrails)
