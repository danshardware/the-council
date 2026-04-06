# The Council — Requirements Index

## Overview

This document indexes all functional and technical requirements for The Council, an AI agent swarm system for enterprise coordination. Requirements are organized into three phases following a critical → important → eventually priority ordering.

## Phase 1 — MVP (Critical)

These requirements form the minimum viable product. They must be completed in order (dependencies flow downward), though stories within a requirement may parallelize.

| ID | Requirement | Description |
|----|------------|-------------|
| [REQ-01](REQ-01_AWS_Infrastructure.md) | Shared Resources | S3 bucket, SSM params. Components deploy own infra |
| [REQ-02](REQ-02_Core_Agent_Framework.md) | Core Agent Framework + LLM | PocketFlow runtime, YAML agents, LLM integration, model routing |
| ~~REQ-03~~ | ~~LLM Integration~~ | *Merged into REQ-02 as stories S03–S04* |
| [REQ-04](REQ-04_Guardrail_Blocks.md) | Guardrail Blocks | Prompt injection (LLM + local classifiers), goal drift, extraction |
| [REQ-05](REQ-05_Agent_Workflow_Engine.md) | Agent Workflow Engine | Thinking → Guardrails → Checkpoint → Action → Decide loop |
| [REQ-06](REQ-06_Memory_System.md) | Memory System | S3 vector-based searchable memory with scopes |
| [REQ-07](REQ-07_Agent_Communication.md) | Agent Communication | Message board, rooms, direct messages (S3-stored) |
| [REQ-08](REQ-08_Core_Tools.md) | Core Tools | File ops, execute, sub-agent, human input, session TODO |
| [REQ-09](REQ-09_Web_Chat_Channel.md) | Web Chat Channel | HTTP polling chat interface (no WebSocket in MVP) |
| [REQ-10](REQ-10_Activity_Dashboard.md) | Activity Dashboard UI | Agent activity history, session inspection, timeline view |
| [REQ-11](REQ-11_Triggering_Scheduling.md) | Triggering & Scheduling | Scheduled actions, AWS Events, chat triggers, agent self-scheduling |

## Phase 2 — Important

These requirements extend the MVP with richer agent capabilities, additional channels, and operational tooling.

| ID | Requirement | Description |
|----|------------|-------------|
| [REQ-12](REQ-12_Long_Term_Agents.md) | Long-term Agent Features | Personality, custom tooling, permissions, memory agent |
| [REQ-13](REQ-13_Short_Term_Agents.md) | Short-term Agents (Contractors) | Scoped workspaces, lifecycle management |
| [REQ-14](REQ-14_Discord_Channel.md) | Discord Channel | Discord bot integration |
| [REQ-15](REQ-15_Extended_Tools.md) | Extended Tools Suite | GitKraken, Kanban, Web browser, approvals, coding tools |
| [REQ-16](REQ-16_Config_Editing_UI.md) | Config & Resource Editing UI | Web-based config/resource editing |

## Phase 3 — Future

These requirements are planned but not immediately needed. Specifications are included for reference and dependency planning.

| ID | Requirement | Description |
|----|------------|-------------|
| [REQ-17](REQ-17_Slack_Channel.md) | Slack Channel | Slack bot integration |
| [REQ-18](REQ-18_Teams_Channel.md) | Teams Channel | Microsoft Teams bot integration |
| [REQ-19](REQ-19_SmithyAI_Tools.md) | SmithyAI Tools Integration | KV Store, Documentation, Vector Store |
| [REQ-20](REQ-20_Deep_Research_Athena.md) | Deep Research & AWS Athena | Research agent patterns, Athena queries |

## Dependency Graph

```
REQ-01 (Shared Resources: S3 + SSM)
  ├── REQ-02 (Agent Framework + LLM Integration)
  │     ├── REQ-04 (Guardrails) ─ incl. local classifiers
  │     │     └── REQ-05 (Workflow Engine)
  │     │           ├── REQ-06 (Memory — S3 vectors)
  │     │           ├── REQ-07 (Communication — S3 messages)
  │     │           └── REQ-12 (Long-term Agents)
  │     │                 └── REQ-13 (Short-term Agents)
  │     ├── REQ-08 (Core Tools)
  │     │     └── REQ-15 (Extended Tools)
  │     └── REQ-11 (Triggering + Self-Scheduling)
  ├── REQ-09 (Web Chat — HTTP polling) ── REQ-14 (Discord) ── REQ-17 (Slack) ── REQ-18 (Teams)
  ├── REQ-10 (Dashboard UI) ── REQ-16 (Config UI)
  └── REQ-19 (SmithyAI) ── REQ-20 (Research/Athena)
```

Note: REQ-03 merged into REQ-02. Each component deploys its own Terraform (Lambda, IAM, API Gateway, etc.) alongside its code.

## Cross-Cutting Concerns

These apply to ALL requirements and are enforced via the [Constitution](../CONSTITUTION.md):

- **Observability**: Every action logged (agent ID, session ID, type, timestamp, I/O, cost)
- **Security**: No secrets in code/memory, prompt injection detection, permission boundaries
- **Cost control**: Cheap models for routine work, expensive models only when justified
- **Testing**: pytest for all acceptance criteria, integration tests, human walkthrough
- **Serverless**: All compute via Lambda, no persistent servers
