# The Council — Implementation Plan

## Overview

Implementation follows a phased approach: MVP (Critical) → Important → Future. Within each phase, requirements are ordered by dependency. Stories within a requirement are ordered sequentially. **Tasks within the same story directory can be executed simultaneously.**

**Storage approach**: S3 (single bucket with prefixes) is the primary data store. DynamoDB is used only for session indexes (query by date/agent) and Kanban board. Each component deploys its own Terraform (Lambda, IAM, API Gateway, etc.) alongside its code.

## Directory Structure

```
Planning/
├── 00_Planning_Index.md              ← This file
├── Phase_1_MVP/
│   ├── 01_AWS_Infrastructure/        ← REQ-01 (Shared Resources)
│   │   └── 01_S01_Shared_Resources/
│   ├── 02_Core_Agent_Framework/      ← REQ-02 (incl. LLM Integration)
│   │   ├── 00_S00_Design/               ← Human collaboration: use cases, schemas, flows
│   │   ├── 01_S01_PocketFlow_Integration/
│   │   ├── 02_S02_Agent_YAML_Definition/
│   │   ├── 03_S03_LLM_Bridge/           ← Conversation API (from old REQ-03)
│   │   ├── 04_S04_Model_Routing_Budget/  ← Model router + token tracking (from old REQ-03)
│   │   ├── 05_S05_Base_Nodes/            ← LLM, Tool, Human, Checkpoint, State nodes
│   │   └── 06_S06_Base_Flows/            ← Ralph Loop, Chain of Thought
│   ├── 04_Guardrail_Blocks/         ← REQ-04 (LLM + local classifiers)
│   │   ├── 01_S01_Prompt_Injection_Detection/
│   │   └── 02_S02_Extraction_Blocks/
│   ├── 05_Agent_Workflow_Engine/     ← REQ-05
│   │   ├── 01_S01_Workflow_Cycle/
│   │   └── 02_S02_Checkpoint_And_Configuration/
│   ├── 06_Memory_System/            ← REQ-06 (S3 vector-based)
│   │   ├── 01_S01_Memory_Storage/
│   │   └── 02_S02_Memory_Search/
│   ├── 07_Agent_Communication/      ← REQ-07 (S3 messages)
│   │   ├── 01_S01_Message_Board/
│   │   └── 02_S02_Message_Routing/
│   ├── 08_Core_Tools/               ← REQ-08
│   │   ├── 01_S01_File_Tools/
│   │   ├── 02_S02_Execute_And_SubAgent/
│   │   └── 03_S03_Human_Interaction_Tools/
│   ├── 09_Web_Chat_Channel/         ← REQ-09 (HTTP polling, no WebSocket)
│   │   ├── 01_S01_HTTP_Backend/
│   │   └── 02_S02_Chat_Frontend/
│   ├── 10_Activity_Dashboard/       ← REQ-10
│   │   ├── 01_S01_Activity_API/
│   │   └── 02_S02_Dashboard_Frontend/
│   └── 11_Triggering_Scheduling/    ← REQ-11 (incl. agent self-scheduling)
│       ├── 01_S01_Schedule_Engine/
│       ├── 02_S02_Event_Mapping/
│       └── 03_S03_Agent_Self_Scheduling/
├── Phase_2_Important/
│   ├── 12_Long_Term_Agents/         ← REQ-12
│   ├── 13_Short_Term_Agents/        ← REQ-13
│   ├── 14_Discord_Channel/          ← REQ-14
│   ├── 15_Extended_Tools/           ← REQ-15
│   └── 16_Config_Editing_UI/        ← REQ-16
└── Phase_3_Future/
    ├── 17_Slack_Channel/             ← REQ-17
    ├── 18_Teams_Channel/             ← REQ-18
    ├── 19_SmithyAI_Tools/            ← REQ-19
    └── 20_Deep_Research_Athena/      ← REQ-20
```

## Execution Rules

1. **Phases are sequential**: Complete Phase 1 before starting Phase 2.
2. **Requirements within a phase are ordered by number**: Complete REQ-01 before REQ-02, etc. (Dependencies enforce this.)
3. **Stories within a requirement are sequential** (numbered 01_, 02_, etc.)
4. **Tasks within a story are parallel**: All `.md` files in the same directory can be worked simultaneously.
5. Each task is executed via the **Ralph Loop** — see [Prompts/ralph_loop.md](../Prompts/ralph_loop.md).
6. All planning and QA validated against the [Constitution](../CONSTITUTION.md).

## Status Tracking

Each task file contains a progress checklist. Roll-up status:

| Phase | Requirement | Status |
|-------|------------|--------|
| 1 | REQ-01: Shared Resources | NOT STARTED |
| 1 | REQ-02: Core Agent Framework + LLM | NOT STARTED |
| 1 | ~~REQ-03~~ | MERGED INTO REQ-02 |
| 1 | REQ-04: Guardrail Blocks | NOT STARTED |
| 1 | REQ-05: Agent Workflow Engine | NOT STARTED |
| 1 | REQ-06: Memory System (S3 vectors) | NOT STARTED |
| 1 | REQ-07: Agent Communication (S3) | NOT STARTED |
| 1 | REQ-08: Core Tools | NOT STARTED |
| 1 | REQ-09: Web Chat (HTTP polling) | NOT STARTED |
| 1 | REQ-10: Activity Dashboard | NOT STARTED |
| 1 | REQ-11: Triggering & Scheduling | NOT STARTED |
| 2 | REQ-12: Long-term Agents | NOT STARTED |
| 2 | REQ-13: Short-term Agents | NOT STARTED |
| 2 | REQ-14: Discord Channel | NOT STARTED |
| 2 | REQ-15: Extended Tools | NOT STARTED |
| 2 | REQ-16: Config Editing UI | NOT STARTED |
| 3 | REQ-17: Slack Channel | NOT STARTED |
| 3 | REQ-18: Teams Channel | NOT STARTED |
| 3 | REQ-19: SmithyAI Tools | NOT STARTED |
| 3 | REQ-20: Deep Research & Athena | NOT STARTED |
