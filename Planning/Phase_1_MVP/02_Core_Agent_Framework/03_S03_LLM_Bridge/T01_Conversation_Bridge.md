# Task: Bridge Conversation API to Agent Framework

## Parent
- **Requirement**: REQ-02 Core Agent Framework
- **Story**: S03 LLM Bridge

## Description
Adapt the existing `Conversation` class (`conversation/conversation.py`) to work as the LLM backend for PocketFlow nodes. Create a provider interface so the LLM Call Node uses the Conversation API transparently.

## Acceptance Criteria
- [ ] **AC-01**: `LLMProvider` interface wraps the `Conversation` class.
- [ ] **AC-02**: `LLMCallNode` uses `LLMProvider` to make calls. Provider is injectable (for testing).
- [ ] **AC-03**: Tool definitions from agent config are automatically registered with the Conversation.
- [ ] **AC-04**: Multi-turn conversations maintain context within a session.
- [ ] **AC-05**: System prompts from agent YAML are correctly set on the Conversation.
- [ ] **AC-06**: Each component deploys its own Lambda + IAM for Bedrock access via Terraform alongside this code.

## QA Checklist
- [ ] pytest tests: provider wrapping, tool registration, system prompt injection, multi-turn state.
- [ ] **Constitution: Simplicity (VII)**: Thin wrapper. Don't duplicate Conversation logic.
- [ ] **Constitution: Security (VI)**: Bedrock access via IAM roles only. No credentials in code.
- [ ] **Coding: Type Hints**: LLMProvider interface fully typed.

## Progress Checklist
- [ ] Task started
- [ ] Tests/validation written
- [ ] Implementation complete
- [ ] All acceptance criteria pass
- [ ] QA checklist validated
- [ ] Human walkthrough completed
