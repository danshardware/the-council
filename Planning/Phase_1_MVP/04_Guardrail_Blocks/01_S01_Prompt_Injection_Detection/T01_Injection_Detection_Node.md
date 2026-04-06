# Task: Prompt Injection Detection Node

## Parent
- **Requirement**: REQ-04 Guardrail Blocks
- **Story**: S01 Prompt Injection Detection

## Description
PocketFlow node that detects prompt injection attempts and non-sequitur content in incoming messages. Uses a pluggable classifier architecture: LLM-based classification via cheap model, with support for local classifiers (e.g., LangChain-based models) for faster/cheaper detection.

## Acceptance Criteria
- [ ] **AC-01**: `PromptInjectionNode` analyzes input text and returns: risk_score (0-1), classification (safe/suspicious/blocked), reasoning.
- [ ] **AC-02**: Known injection patterns (ignore previous, system prompt override, role-play attacks) are detected.
- [ ] **AC-03**: Normal conversational messages pass without false positives.
- [ ] **AC-04**: Non-sequitur content (random unrelated text) is flagged as suspicious.
- [ ] **AC-05**: Blocked content raises a clear rejection with explanation.
- [ ] **AC-06**: Classifier backend is pluggable via interface: `LLMClassifier` (cheap Bedrock model) and `LocalClassifier` (LangChain-based). Configurable per-agent.
- [ ] **AC-07**: At least one local classifier option available (e.g., LangChain's prompt injection classifier) as an alternative to LLM-based detection.

## QA Checklist
- [ ] pytest tests: injection patterns, benign messages, edge cases, non-sequiturs, local classifier fallback.
- [ ] **Constitution: Security (VI)**: All external input runs through this node.
- [ ] **Constitution: Cost-Conscious (IV)**: Local classifiers preferred for routine checks. LLM for ambiguous cases.
- [ ] **Constitution: Observability (V)**: Detection decisions logged with classifier used and reasoning.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
