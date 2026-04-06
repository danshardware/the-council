# The Council Constitution

## Core Principles

### I. Serverless-First
All infrastructure must be serverless on AWS. No long-standing resources (EC2 instances, ECS clusters, always-on containers). Every component runs as Lambda, Bedrock, or a managed service that scales to zero. Terraform provisions everything; local backend for now.

### II. Agent Modularity
Agents are defined declaratively via YAML and composed from PocketFlow nodes and flows. Every agent is independently deployable, testable, and replaceable. Agents may create sub-agents on the fly for specialized tasks. No monolithic agent designs.

### III. Test-First (NON-NEGOTIABLE)
TDD is mandatory. Tests are written before implementation. The cycle is: Write tests → Tests fail (Red) → Implement (Green) → Refactor. Use pytest exclusively. Do not mock AWS services — test against real behavior or use contract/integration tests with actual AWS resources in a dev environment. Every acceptance criterion must have a corresponding automated test.

### IV. Cost-Conscious LLM Usage
Expensive models (Claude Opus, GPT-4 class) are reserved for complex reasoning, planning, and creative tasks only. All routine operations (extraction, classification, formatting, guardrails) use the cheapest viable model. Token usage is tracked and logged per-agent, per-session. Budget guardrails halt runaway spending.

### V. Observability & Auditability
Every agent action is logged with: agent ID, session ID, action type, timestamp, inputs, outputs, and cost. Logs are structured for easy filtering and replay. The activity UI renders these logs as an inspectable timeline. No silent failures — every error is captured, categorized, and surfaced.

### VI. Security by Default
No credentials in code, config, or memory. All secrets come from environment variables or AWS Secrets Manager. Agent memory cannot store passwords or secrets. All external inputs (chat messages, webhook payloads, agent-to-agent messages) are treated as untrusted. Prompt injection detection runs on every inbound message. File and command execution tools operate within explicit permission boundaries.

### VII. Simplicity & YAGNI
Start simple. Build only what is needed for the current requirement. No speculative abstractions, no premature optimization, no infrastructure "just in case." Every piece of complexity must be justified by a current, concrete need. When in doubt, leave it out.

### VIII. Human-in-the-Loop Checkpoints
Irreversible actions (deployments, external communications, financial operations, data deletion) require human approval. Agents must checkpoint before destructive operations. The board gates all work — agents propose, humans approve.

## AWS Architecture Constraints

- **Compute**: AWS serverless, for all processing. No EC2, no ECS, no Fargate for persistent workloads. Temporary containers are allowed.
- **LLM**: Amazon Bedrock for model inference. Conversations API wrapper for all LLM calls.
- **Agent Orchestration**: Bedrock AgentCore for major workflows.
- **Storage**: S3 for files, KV data, and general storage (single bucket with prefixes). DynamoDB only for session indexes (queryable by date/agent) and Kanban board. CodeCommit for code repositories.
- **IaC**: Terraform (latest) with latest AWS provider. Local backend. Region and account from environment.
- **Runtime**: Python 3.14.
- **No long-standing resources**: Everything must scale to zero when idle.

## Development Workflow

1. **Requirement → Stories → Tasks**: All work traces back to a numbered requirement with acceptance criteria.
2. **Ralph Loop Execution**: Tasks are executed via the Ralph loop pattern — autonomous iterative implementation with file-based progress tracking and git commits.
3. **Constitution Check at Planning**: Every story and task plan is validated against this constitution before implementation begins.
4. **Constitution Check at QA**: Every completed task is validated against this constitution during review. Non-conformance blocks merging.
5. **QA Checklist**: Every task includes unit tests, integration tests, and a human walkthrough. Antipatterns derived from this constitution and the Python coding guidance are explicitly checked.

## Quality Gates

- **Unit Tests**: All acceptance criteria have corresponding pytest tests. Tests pass before code is considered complete.
- **Integration Tests**: Cross-component interactions are tested. Agent workflow cycles, message board routing, memory retrieval, and tool invocations all have integration coverage. Tests must work on target infrastructure.
- **Human Walkthrough**: A human reviews the implementation, runs the tests, and confirms the feature works as designed before the task is marked done. Intermediate steps in a workflow should be visible to validate operation.
- **Constitution Compliance**: Code is reviewed against each applicable principle above. Violations are blockers.

## Coding Standards

- Follow PEP 8 within reason. Lines ≤ 79 characters.
- Type hints on all function signatures (use `typing` module).
- Docstrings on all public functions (PEP 257).
- Descriptive function and variable names.
- Handle edge cases explicitly. Clear exception handling at system boundaries.
- No defensive coding for impossible scenarios. Trust internal code.

## Governance

This constitution supersedes all other development practices for The Council project. Amendments require:
1. A written proposal documenting the change and rationale.
2. Board approval.
3. A migration plan for any existing code that becomes non-conformant.

All code reviews, planning sessions, and QA checks must verify compliance with this constitution.

**Version**: 1.0.0 | **Ratified**: 2026-04-03 | **Last Amended**: 2026-04-03
