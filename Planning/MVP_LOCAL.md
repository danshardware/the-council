# Council — Local MVP Plan

> **Goal**: A fully local (remote LLMs via Bedrock), no-UI agent system where YAML-defined agents run on schedules, use tools, talk to each other asynchronously, store and retrieve memory, and are fully traceable — validatable with a CEO agent delegating to sub-agents without going off the rails.

---

## Non-Goals (for this MVP)

- No web UI, dashboard, or API server
- No AWS infrastructure (Lambda, S3, DynamoDB, SQS, EventBridge)
- No long-term vs. short-term agent distinction at the code level
- No Discord / Slack / Teams channels
- No prompt injection ML classifier (LLM-based guardrail only)

---

## Tech Stack

| Concern | Choice | Reason |
|---|---|---|
| LLM | AWS Bedrock (boto3) | Existing `conversation.py`; Claude + Nova + specialized |
| Agent flow framework | PocketFlow (copy into repo) | Already planned; 100-line core, extensible |
| Local vector store | ChromaDB (in-process) | No server, persists to disk, good metadata filtering |
| Scheduling | APScheduler (in-process) | Lightweight, no infra, YAML-backed job store |
| CLI / console | Rich | Pretty live output, minimal code |
| Config / definitions | PyYAML | YAML agent + flow definitions |
| Python | 3.12+ | Stable, available locally |

---

## Directory Layout

```
d:\dev\Council\
  agents/                    # YAML agent definitions
    ceo.yaml
    researcher.yaml

  flows/                     # YAML flow (workflow graph) definitions
    main_loop.yaml
    inbox_handler.yaml

  tools/                     # Tool implementations
    __init__.py              # Tool registry + @tool decorator
    file_tools.py            # read_file, write_file, list_files, delete_file
    command_tools.py         # run_command (allowlist/denylist enforced)
    message_tools.py         # send_message, check_inbox
    agent_tools.py           # spawn_agent (sync), send_to_agent (async mailbox)
    memory_tools.py          # store_memory, search_memory, update_memory, delete_memory
    schedule_tools.py        # schedule_agent, cancel_schedule, list_schedules

  engine/                    # Core runtime
    __init__.py
    runner.py                # AgentRunner: loads agent+flow YAML, drives execution
    block.py                 # Block types: llm, tool_call, guardrail, checkpoint, human_input
    flow_loader.py           # Parses flow YAML → executable graph (dict of Block)
    llm.py                   # Bedrock LLM bridge (wraps conversation.py + adds tool schema injection)
    logger.py                # JSONL trace writer
    state.py                 # AgentState: serialise/deserialise to/from checkpoint JSON
    scheduler.py             # APScheduler wrapper; reads/writes config/schedules.yaml
    mailbox.py               # Mailbox: write message, poll/watch inbox, trigger runner on arrival

  memory/
    __init__.py
    store.py                 # ChromaDB wrapper: store/search/update/delete
    cluster.py               # Two-stage retrieval: topic-cluster first, then semantic search

  pocketflow/                # PocketFlow source (copied in)
    __init__.py              # Node, Flow, BatchNode, BatchFlow (~100 lines)

  workspace/                 # Agent sandboxed working directory
    ceo/
    researcher/

  logs/                      # Trace logs
    {agent_id}/
      {session_id}.jsonl     # One JSONL entry per action/event

  messages/                  # Async mailbox
    {agent_id}/
      inbox/
        {msg_id}.yaml

  memory_db/                 # ChromaDB on-disk persistence

  config/
    schedules.yaml           # APScheduler job definitions

  conversation/              # Existing Bedrock wrapper (unchanged)
    conversation.py

  run.py                     # CLI: python run.py --agent ceo --prompt "..."
  requirements.txt
```

---

## YAML Schemas

### Agent Definition (`agents/ceo.yaml`)

```yaml
id: ceo
name: CEO
description: |
  Strategic orchestrator. Receives objectives, delegates research and planning
  to sub-agents, synthesises results, and maintains institutional memory.

flows:
  main: main_loop          # invoked by CLI / schedule
  inbox: inbox_handler     # invoked when a mailbox message arrives

max_iterations: 20         # runner-level hard cap for this agent (overrides global)

model_defaults:
  provider: bedrock
  model_id: us.anthropic.claude-opus-4-5

permissions:
  workspace_paths:
    - workspace/ceo/
  allowed_commands: []     # no shell commands for CEO

memory:
  realms:
    - institutional
    - knowledge_base
    - sop
```

### Flow Definition (`flows/main_loop.yaml`)

```yaml
id: main_loop
max_iterations: 15         # flow-level cap (lower of flow vs. runner wins)
start: think

blocks:

  think:
    type: llm
    model_id: us.anthropic.claude-opus-4-5          # override agent default
    system_prompt: |
      You are the CEO. Your job is to drive improvements in your current company and help the board to implement their plans. Work closely with them to find the best possible way to acheive their goals while remaining ethical. Your time is precious so be sure to delegate any tasks that you can and save your thinking power for things only you can do.
      
      Analyse your current context and decide what to do next.
      
      You MUST respond with valid YAML:
      ```yaml
      reasoning: "<your thinking>"
      action: "<action_name>"  # delegate_task | do_research | write_memory | done
      action_input:
        key: value
      ```
    tools:
      - search_memory
      - read_file
      - list_files
    transitions:
      delegate_task: pre_action_guard
      do_research: research_block
      write_memory: write_memory_block
      done: END
      default: think         # unexpected output loops back

  pre_action_guard:
    type: guardrail
    model_id: amazon.nova-lite-v1:0
    system_prompt: |
      You are a safety reviewer. Will the following action result in ANY of these:
        - Spending real money
        - Sending external communications (email, SMS, webhooks)
        - Deleting files permanently
        - Irreversible system changes
      Respond ONLY with valid YAML:
      ```yaml
      verdict: approved  # approved | needs_confirmation | rejected
      reason: "..."
      ```
    transitions:
      approved: delegate_block
      needs_confirmation: human_checkpoint
      rejected: think

  human_checkpoint:
    type: human_input
    prompt: "Agent requires confirmation before proceeding. Approve? [y/n]: "
    transitions:
      approved: delegate_block
      rejected: think

  delegate_block:
    type: llm
    model_id: us.anthropic.claude-opus-4-5
    system_prompt: |
      Compose a delegation task. Respond with valid YAML:
      ```yaml
      action: sync_spawn  # sync_spawn | async_send
      target_agent: "<id>"
      prompt: "..."
      ```
    tools:
      - spawn_agent          # sync: wait for result
      - send_message         # async: fire-and-forget, checkpoint self
    transitions:
      sync_spawn: post_action_guard
      async_send: checkpoint_and_suspend
      done: END

  checkpoint_and_suspend:
    type: checkpoint
    mode: mailbox            # serialise state; resume when inbox reply arrives
    timeout_hours: 24
    on_timeout: think

  post_action_guard:
    type: guardrail
    model_id: amazon.nova-lite-v1:0
    system_prompt: |
      Review this tool result. Did anything unexpected happen?
      Respond ONLY with valid YAML:
      ```yaml
      verdict: approved  # approved | flagged
      reason: "..."
      ```
    transitions:
      approved: think
      flagged: human_checkpoint

  research_block:
    type: llm
    model_id: us.anthropic.claude-sonnet-4-5
    system_prompt: |
      Research the given topic using available tools.
      Respond with valid YAML:
      ```yaml
      action: store_finding  # store_finding | done
      content: "..."
      topic: "..."
      ```
    tools:
      - search_memory
      - read_file
      - store_memory
    transitions:
      store_finding: think
      done: think

  write_memory_block:
    type: tool_call
    tool: store_memory
    transitions:
      default: think
```

---

## Block Types

| Type | What it does |
|---|---|
| `llm` | Calls Bedrock with system prompt + tool schemas for this block. Parses `action:` and `action_input:` fields from YAML response. Routes via `transitions`. |
| `tool_call` | Directly invokes a named tool with the current state's `action_input`. No LLM call. |
| `guardrail` | LLM call with a specific safety prompt. Parses `verdict:` field from YAML response. Routes via `transitions`. |
| `checkpoint` | Serialises agent state to disk. In `mailbox` mode: exits runner and waits for inbox. In `human` mode: prompts stdin and waits. |
| `human_input` | Pauses, prints prompt to Rich console, reads stdin. Verdict routes transitions. |

---

## Tool Registration

All tools are registered centrally via a `@tool` decorator that captures name, description, parameter schema, and the auth context needed. The LLM bridge only injects schemas for tools listed in the current block's `tools:` list.

```python
@tool(
    name="read_file",
    description="Read a file from the agent's workspace.",
    params={"path": "string"}
)
def read_file(path: str, context: ToolContext) -> str:
    ...
```

`ToolContext` carries: `agent_id`, `session_id`, `allowed_paths`, `allowed_commands` — so every tool can enforce its own permission boundary without a separate layer.

---

## Trace Logging

Every event written to `logs/{agent_id}/{session_id}.jsonl`:

```json
{"ts": "2026-04-06T10:23:01Z", "agent_id": "ceo", "session_id": "abc123",
 "event": "block_enter", "block": "think", "iteration": 1}

{"ts": "2026-04-06T10:23:03Z", "agent_id": "ceo", "session_id": "abc123",
 "event": "llm_call", "block": "think", "model": "claude-opus-4-5",
 "input_tokens": 412, "output_tokens": 87, "cost_usd": 0.0024}

{"ts": "2026-04-06T10:23:03Z", "agent_id": "ceo", "session_id": "abc123",
 "event": "transition", "from": "think", "to": "pre_action_guard",
 "action": "delegate_task"}

{"ts": "2026-04-06T10:23:04Z", "agent_id": "ceo", "session_id": "abc123",
 "event": "tool_call", "tool": "spawn_agent", "input": {...}, "output": {...},
 "duration_ms": 3200}
```

---

## Async Mailbox Protocol

```
Agent A (ceo, session S1) delegates async to Agent B (researcher):

1. CEO calls send_message(target="researcher", prompt="...", reply_to_session="S1")
   → writes messages/researcher/inbox/{msg_id}.yaml
     from: ceo
     from_session: S1
     reply_to: messages/ceo/inbox/
     prompt: "..."

2. CEO enters checkpoint block (mode: mailbox)
   → serialises state to logs/ceo/S1_checkpoint.yaml
   → adds a watch entry to config/schedules.yaml:
     type: mailbox_watch
     agent: ceo
     session: S1
     timeout: "2026-04-07T10:23Z"
   → runner exits cleanly

3. Mailbox watcher (APScheduler polling job, every 10s) sees new file in
   messages/researcher/inbox/
   → spawns runner: AgentRunner(agent="researcher", flow="inbox_handler", input=msg)

4. Researcher completes its task, writes:
   → messages/ceo/inbox/{reply_id}.yaml
     from: researcher
     from_session: S2
     reply_to_session: S1
     content: "..."

5. Mailbox watcher sees reply for session S1 in ceo/inbox
   → loads logs/ceo/S1_checkpoint.json
   → resumes AgentRunner from checkpoint_and_suspend block with reply as input
```

---

## Memory Design

### Collections (ChromaDB)

| Collection name | `realm` tag | Contents |
|---|---|---|
| `knowledge_base` | `knowledge_base` | Documents, research, reference material |
| `institutional` | `institutional` | Episodic: dated events, outcomes, lessons learned |
| `sop` | `sop` | Standard operating procedures, decision rules |

All collections are **shared** (any agent can read/write any realm).

### Document Metadata Schema

```yaml
realm: institutional
topic: market_research
keywords:
  - competitor
  - pricing
  - Q1 2026
agent_id: researcher
session_id: S2
timestamp: "2026-04-06T10:30:00Z"
```

### Two-Stage Retrieval

1. **Cluster step**: Embed the query, compare against pre-computed topic centroid embeddings (one per `topic` value in the collection). Select top-K topics.
2. **Search step**: Full semantic search within ChromaDB, filtered to those K topics. Return ranked results with combined score.

`cluster.py` maintains a `topic_centroids` collection that is updated whenever a new topic is first used. Retrieving by a novel question won't miss existing material because the cluster step casts a wide net before the precise search narrows it.

---

## Iteration Guard

Two-level protection against infinite loops:

| Level | Where set | Default | Behaviour |
|---|---|---|---|
| Runner hard cap | `agent.yaml → max_iterations` | 50 | Raises `MaxIterationsError`, logs, exits cleanly |
| Flow cap | `flow.yaml → max_iterations` | 25 | Same, but per flow instance |
| Per-block | Any block can set `max_visits: N` | — | Prevents a single block dominating |

The lower of (runner cap, flow cap) wins. A `MaxIterationsError` is logged as a trace event and triggers a `human_input` block if one is configured as `on_max_iterations` in the flow.

---

## Build Layers (Sequential — each independently testable)

### Layer 1 — Core Loop
**Ships**: PocketFlow copy, YAML agent loader, YAML flow loader, Bedrock LLM bridge, JSONL logger, `rich` console, `run.py` CLI  
**Not included**: tools, guardrails, memory, mailbox  
**Test**: `python run.py --agent ceo --prompt "Say hello and stop"` → 3 iterations visible in Rich console + JSONL log

### Layer 2 — Flow Engine
**Ships**: All block types (llm, tool_call, guardrail, checkpoint, human_input), transition routing, iteration guards  
**Test**: Define a 3-block flow; verify agent routes based on action output; verify loop cap fires

### Layer 3 — Tools (Core)
**Ships**: Tool registry + `@tool` decorator, `file_tools.py`, `command_tools.py`, permission enforcement via `ToolContext`  
**Test**: Agent reads a file in its workspace path; is blocked reading outside it; runs an allowed command; blocked on a denied command

### Layer 4 — Guardrails + Human Input
**Ships**: Guardrail block execution, human_input block, stdin integration, Rich confirmation prompt  
**Test**: Trigger a flagged action, see it rerouted; trigger human_input, respond "n", verify reroute

### Layer 5 — Memory (ChromaDB)
**Ships**: `memory/store.py`, `memory/cluster.py`, `memory_tools.py`, shared collection setup  
**Test**: Agent A stores a finding; Agent B retrieves it with a natural language question; two-stage retrieval returns correct result

### Layer 6 — Mailbox + Async Comms
**Ships**: `engine/mailbox.py`, `message_tools.py`, `engine/state.py` (checkpoint/resume), APScheduler watch job  
**Test**: CEO sends async message → checkpoints; researcher picks it up → runs → replies; CEO resumes with reply content

### Layer 7 — Scheduling
**Ships**: `engine/scheduler.py`, `schedule_tools.py`, `config/schedules.json` management  
**Test**: Schedule CEO to run in 1 minute; it fires at the right time; agent can schedule itself from within a flow

---

## First Smoke Test (Acceptance Criteria for MVP)

1. `ceo.yaml` loaded; flow `main_loop.yaml` loaded; no errors
2. CEO runs 3 iterations without looping infinitely
3. CEO delegates a task to `researcher` via sync spawn; researcher returns a result; CEO logs it
4. CEO delegates a task to `researcher` via async mailbox; CEO checkpoints; researcher runs; CEO resumes
5. A guardrail fires and redirects back to `think` without executing the action
6. A `max_iterations` cap fires and exits cleanly with a log entry
7. A memory entry stored by `researcher` is retrievable by `ceo` using a natural language question
8. `logs/ceo/{session_id}.jsonl` contains a complete trace of all events including token counts
9. APScheduler fires CEO on a 1-minute schedule and the run is traceable

---

## Key Design Decisions (captured)

| Decision | Choice | Rationale |
|---|---|---|
| Tool availability | Per-block, not per-agent | Lets complex flows restrict context precisely |
| Unlisted tool in block | Silently unavailable (not injected into schema) | LLM can't call what it can't see; no guardrail noise |
| Sub-agent invocation | Sync (`spawn_agent`) + async (`send_message`) | Sync for scatter-gather; async for fire-and-forget delegation |
| Guardrails | Explicit blocks in flow graph, not middleware | Testable, skippable per flow, visible in trace |
| Memory retrieval | Two-stage (topic cluster → semantic search) | Reduces miss rate on novel queries |
| Iteration cap | Both runner-level and flow-level (lower wins) | Defense in depth |
| Traceability | JSONL per session under `logs/{agent_id}/` | Greppable, appendable, no DB required |
| Scheduling | APScheduler + YAML config | No AWS infra; observable; agents can self-schedule |
