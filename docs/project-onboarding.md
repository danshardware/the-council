# Council — Project Onboarding

This document exists for an LLM (or human) picking up this codebase cold. Read it instead of trawling every file.

---

## What this is

A local multi-agent system. Multiple AI agents (backed by AWS Bedrock) run concurrently, communicate via an async file-based mailbox, share a ChromaDB memory store, and can spawn sub-agents or schedule future work. There is no cloud infrastructure yet — everything runs locally with `uv run`.

---

## Stack

| Concern | Choice |
|---|---|
| Python | 3.12, managed by `uv` |
| LLM API | AWS Bedrock via `boto3` |
| Agent framework | PocketFlow (vendored at `pocketflow/__init__.py`) |
| Vector memory | ChromaDB + Bedrock Titan Embeddings v2 |
| Scheduling | APScheduler |
| CLI display | Rich |
| Agent/flow config | YAML |

**AWS Bedrock models in use:**
- CEO agent: `us.anthropic.claude-opus-4-5-20251101-v1:0`
- Researcher agent: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`
- Guardrail blocks: `us.amazon.nova-lite-v1:0`
- Embeddings: `amazon.titan-embed-text-v2:0`

---

## Directory map

```
agents/           YAML definitions for each agent (id, model, flows, permissions, memory, context_files)
config/           schedules.yaml — persistent APScheduler schedule definitions
conversation/     Bedrock conversation API wrapper (BedrockTool, converse call)
engine/
  block.py        All PocketFlow block types (LLMBlock, GuardrailBlock, ToolCallBlock, CheckpointBlock, HumanInputBlock)
  flow_loader.py  Parses flow YAML → PocketFlow Flow graph
  llm.py          Bedrock LLM bridge with retry + exponential backoff
  logger.py       JSONL trace writer (logs/<agent>/<session>.jsonl)
  mailbox.py      File-based async mailbox (messages/<agent>/inbox/, /processed/)
  runner.py       AgentRunner — wires shared state, loads agent+flow, drives execution
  scheduler.py    APScheduler wrapper + mailbox poller
  state.py        Checkpoint serialisation (saves/loads shared state)
flows/            YAML flow definitions (graph of blocks + transitions)
logs/             JSONL traces, one file per session
memory/
  store.py        MemoryStore class — ChromaDB collections, BedrockEmbeddingFunction
  pipeline.py     PocketFlow import pipeline (FileReader→Cleaner→Chunker→Embedder)
memory_db/        ChromaDB persistence directory
messages/         Agent mailboxes (inbox/, processed/ per agent)
pocketflow/       Vendored PocketFlow framework (~200 lines)
shared_knowledge/ Context files auto-injected into LLM system prompts via context_files: in agent YAML
tools/
  __init__.py     @tool decorator, ToolContext dataclass, global registry, BedrockTool binding
  agent_tools.py  spawn_agent, send_message
  command_tools.py run_command (allowlisted executables only)
  file_tools.py   read_file, write_file, list_files, delete_file, file_exists
  memory_tools.py store_memory, search_memory, update_memory, delete_memory
  message_tools.py check_inbox, mark_message_processed
  schedule_tools.py schedule_agent, cancel_schedule, list_schedules
workspace/        Per-agent scratch space (workspace/<agent_id>/)
wunderite-docs/   Separate reference project (crawl4ai-based doc crawler) — not part of Council
memory.py         CLI for managing ChromaDB memory (list/add/search/edit/delete/import)
run.py            CLI entry point — runs an agent or starts the scheduler daemon
```

---

## How to run

```bash
# Run an agent with a prompt
uv run run.py --agent ceo --prompt "Draft a strategy for entering the Nigerian market"

# Run on a specific flow (default is 'main')
uv run run.py --agent researcher --prompt "Summarise our product roadmap" --flow main

# Start the daemon (mailbox poller + scheduled jobs)
uv run run.py --daemon --poll-seconds 10

# Memory CLI
uv run memory.py list --realm knowledge_base
uv run memory.py search "product strategy"
uv run memory.py import shared_knowledge/company/ --topic "company overview" --realm institutional
```

---

## Core concepts

### Agent YAML (`agents/<id>.yaml`)
Defines the agent: which models to use, which flows it has, what workspace paths it's allowed to touch, which memory realms it can access, and which shared knowledge files to inject into its system prompts.

### Flow YAML (`flows/<id>.yaml`)
A graph of blocks. Each block has a type, optional model/tools/prompt config, and a `transitions` map (action string → next block id, or `END`). The `start:` key names the first block.

### Block types
- `llm` — calls Bedrock, parses YAML response, returns action string
- `guardrail` — same as llm but styled as a safety reviewer; returns `approved/rejected/flagged`
- `tool_call` — invokes one named tool from the registry, injects result into messages
- `checkpoint` — serialises shared state to disk, then raises `SuspendExecution` (agent halts, resumable)
- `human_input` — prints a prompt, reads stdin, maps response to approved/rejected

### Shared state
A single `dict` passed through all blocks in a session. Key fields:
- `messages` — conversation history (Bedrock-format list of role/content dicts)
- `agent_id`, `session_id`
- `agent_config` — full parsed agent YAML
- `tool_context` — `ToolContext(agent_id, session_id, allowed_paths, allowed_commands)`
- `context_injection` — pre-built XML blocks from `context_files:` in agent YAML
- `iteration`, `block_visits` — loop guard counters
- `logger` — Logger instance

### Tool system
Any function decorated with `@tool` in any file that is imported at startup is auto-registered. Tools must accept `context: ToolContext` as their last parameter. The `@tool` decorator strips `context` from the Bedrock-visible schema so the LLM only sees domain parameters. Tools are listed explicitly in flow YAML under each `llm` block (`tools: [name, ...]`).

### Memory
Three ChromaDB collections (realms): `knowledge_base`, `institutional`, `sop`. All agents share the same collections. Two-stage retrieval: topic centroid search, then full semantic search within matched topics. Embeddings via Bedrock Titan v2.

### Mailbox
File-based. `send()` writes a YAML file to `messages/<agent>/inbox/`. `poll_inbox()` reads them. `mark_processed()` moves file to `processed/`. The daemon polls mailboxes every N seconds and triggers the agent's `inbox` flow when messages arrive.

### Logging
Every session writes a JSONL trace to `logs/<agent_id>/<session_id>.jsonl`. Events include `session_start`, `block_enter`, `llm_call` (with full message history), `tool_call`, `guardrail`, `session_end`, `error`.

---

## What's working

All core layers are implemented and tested via real agent runs:
- CEO agent delegates to Researcher agent (sync and async)
- Researcher writes reports to workspace, exits via guardrail-checked write
- Guardrail blocks screen proposed actions
- Memory store/search across agents
- Scheduler daemon + self-scheduling via `schedule_agent` tool
- Mailbox messaging between agents
- Memory CLI (`memory.py`) with PocketFlow import pipeline
- Shared knowledge injection via `context_files:` in agent YAML

---

## Known constraints

- No internet access from agents — tools are file/memory/scheduling/messaging only
- `run_command` requires executable to be explicitly listed in `permissions.allowed_commands` in agent YAML; default is empty (no commands allowed)
- Bedrock `read_timeout` is 300s; LLM calls retry up to 3 times with exponential backoff on transient errors
- Windows: all file I/O uses UTF-8 with latin-1 fallback on read
- ChromaDB collection names must be alphanumeric + hyphens, 3–63 chars
