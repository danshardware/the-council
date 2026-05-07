# AGENTS.md — Council Codebase Reference

This document is written for a coding agent. Read it before touching any file.

---

## What This Is

A local multi-agent system. Multiple AI agents (backed by AWS Bedrock) run concurrently, communicate via a file-based async mailbox, share a ChromaDB vector memory store, and can spawn sub-agents or schedule future work.

Agents and their flows are defined entirely in YAML. No Python is needed to create a new agent unless it requires a new tool.

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
| Prompt templating | Mustache (`chevron`) |

---

## Directory Map

```
agents/           YAML definitions for default, included agents
config/           Static config YAMLs (guardrails, schedules, discord)
conversation/     Bedrock Converse API wrapper (BedrockTool, Conversation class)
data/             Mutable runtime state (mounted as a volume in production)
engine/
  block.py        All block types: LLMBlock, GuardrailBlock, ToolCallBlock,
                  CheckpointBlock, HumanInputBlock, SetStateBlock
  flow_loader.py  Parses flow YAML → PocketFlow Flow graph
  llm.py          Bedrock LLM bridge with retry + exponential backoff
  logger.py       JSONL trace writer (logs/<agent>/<session>.jsonl)
  mailbox.py      File-based async mailbox
  paths.py        Central path constants; respects COUNCIL_DATA_DIR env var
  runner.py       AgentRunner — wires state, loads agent+flow, drives execution
  scheduler.py    APScheduler wrapper + mailbox poller
  state.py        Checkpoint save/load
  template.py     Mustache prompt renderer
flows/            YAML flow definitions for default agents
memory/           ChromaDB store + import pipeline
pocketflow/       Vendored PocketFlow framework (~200 lines, do not modify)
tests/            pytest suite
tools/            Tool registry + all built-in tools
```

---

## How to Run

```bash
# Install dependencies
uv sync

# Run a single agent
uv run run.py --agent concierge --prompt "Hello"

# Run on a specific named flow
uv run run.py --agent researcher --prompt "Summarise our roadmap" --flow main

# Start the daemon (mailbox poller + scheduler + Discord gateway)
uv run run.py --daemon

# Start daemon in local dev mode (no channel gateways)
uv run run.py --daemon --local

# Memory CLI
uv run memory.py list --realm knowledge_base
uv run memory.py search "product strategy"
```

---

## PocketFlow — How It Works

PocketFlow is the execution engine. It is vendored in `pocketflow/__init__.py`. **Do not modify it.**

### Core Model

A **Flow** is a directed graph of **Nodes**. Each node has three lifecycle methods:

```
prep(shared)        → prep_res
exec(prep_res)      → exec_res
post(shared, prep_res, exec_res)  → action_string
```

- `prep`: read from `shared`, prepare inputs
- `exec`: do the work (LLM call, tool call, etc.)
- `post`: write results back to `shared`, return an action string

The **action string** returned by `post` selects the next node via `successors`. If no matching successor exists, the flow ends.

### Shared State

`shared` is a plain `dict` passed to every node. It is the only communication channel between nodes. Key fields set by the runner:

| Key | Type | Description |
|---|---|---|
| `agent_id` | `str` | Agent identifier |
| `session_id` | `str` | Unique session identifier |
| `messages` | `list` | Rolling conversation log (capped at 12) |
| `action` | `str` | Last action string from LLM |
| `action_input` | `dict` | Last action_input dict from LLM |
| `reasoning` | `str` | Last reasoning string from LLM |
| `tool_context` | `ToolContext` | Tool permissions context |
| `agent_config` | `dict` | Parsed agent YAML |
| `max_iterations` | `int` | Hard cap for this session |
| `iteration` | `int` | Current iteration count |
| `_conv` | `Conversation` | Live Bedrock conversation object |
| `_conv_turns` | `list` | Serialised conversation for checkpoints |
| `_input_guardrail_prompt` | `str` | Resolved system prompt for input safety checks (agent override or system default) |
| `_output_guardrail_prompt` | `str` | Resolved system prompt for output safety checks (agent override or system default) |
| `write_paths` | `list[str]` | Stable writable dirs from permissions |
| `read_paths` | `list[str]` | Read-only dirs from permissions |

Keys starting with `_` are private/internal. Do not write to them from tools or flow YAML.

### Node Lifecycle (what the framework calls)

```python
# For a sync Node:
curr.set_params(params)
action = curr._run(shared)
#  _run calls: prep → _exec (wraps exec with retries) → post
next_node = flow.get_next_node(curr, action)
```

Transitions: `node.next(other_node, action="some_action")` or in YAML via `transitions:`.

---

## Block Types (engine/block.py)

All block types are `Node` subclasses. They are instantiated by `flow_loader.py` from YAML config.

### `llm`

Calls Bedrock. Renders the system prompt via Mustache. Parses a YAML response from the LLM. Returns the `action` field as the transition string.

```yaml
think:
  type: llm
  model_id: us.anthropic.claude-sonnet-4-5-20250929-v1:0  # optional; uses agent default if absent
  system_prompt: |
    You are an analyst.

    Respond ONLY with valid YAML:
    ```yaml
    reasoning: "your thinking"
    action: search | write | done
    action_input:
      query: "..."  # fields depend on action
    ```
  tools:
    - search_memory
    - read_file
  transitions:
    search: search_block
    write: write_block
    done: END
    default: think  # ALWAYS include a default fallback
```

**Rules for `llm` blocks:**
- Always include a `default:` transition to handle unexpected LLM output
- The system prompt must instruct the LLM to respond ONLY with YAML in the exact format shown
- Tool schemas and workspace paths are auto-injected — do not duplicate them in the prompt
- `context_files` from the agent YAML are auto-prepended to every system prompt

### `guardrail`

Same as `llm` but purpose-built for reviewing a proposed action. Use a cheap model (`nova-lite`). Returns `verdict` as the transition string.

```yaml
guard:
  type: guardrail
  model_id: us.amazon.nova-lite-v1:0
  system_prompt: |
    Review the proposed action for safety issues.
    Respond ONLY:
    ```yaml
    verdict: approved   # approved | needs_confirmation | rejected
    reason: "..."
    ```
  transitions:
    approved: next_block
    needs_confirmation: human_checkpoint
    rejected: fallback_block
    default: fallback_block
```

A rejected verdict automatically injects a `[SYSTEM]` message into the conversation so the LLM knows its action was blocked.

**Built-in Guardrail Prompts (Automatic):**

Two system-level guardrails run automatically in every agent session:
- **Input safety** (`_input_guardrail_prompt`): Checks incoming user prompts for injection attacks, harmful content, and off-topic abuse before the flow starts. Verdicts: `approved` (proceed), `warn` (proceed + inject warning), `rejected` (block flow).
- **Output safety** (`_output_guardrail_prompt`): Checks each LLM block's proposed action before transition. Catches scope creep, prompt injection echoes, and data exfiltration. Verdicts: `approved` (proceed), `warn` (proceed + inject warning), `rejected` (retry block).

Both use the default system prompts from `config/guardrails.yaml` (`input_safety` and `output_safety` keys). Agents may override them in their YAML config (see **Agent YAML Structure** below).

### `tool_call`

Calls one registered tool directly — no LLM. Reads `shared["action_input"]` (set by the preceding LLM block), passes it to the tool, appends result to `shared["messages"]`. Always returns `"default"`.

```yaml
search_block:
  type: tool_call
  tool: search_memory   # must match a @tool function name
  input_keys: [query]   # optional: whitelist which action_input keys to forward
  transitions:
    default: think
```

### `checkpoint`

Saves full session state to disk and raises `SuspendExecution`. The agent halts and can be resumed later.

```yaml
wait_for_reply:
  type: checkpoint
  transitions:
    default: resume_block  # executed on resume
```

### `human_input`

Prints a prompt to stdout, reads one line from stdin. Maps `y`/`yes` → `approved`, anything else → `rejected`.

```yaml
confirm:
  type: human_input
  prompt: "Approve this action? [y/n]: "
  transitions:
    approved: proceed_block
    rejected: cancel_block
```

### `human_reply`

Displays `action_input.message` and reads free-text input from stdin. Returns `replied`.

```yaml
ask_user:
  type: human_reply
  transitions:
    replied: process_reply_block
```

### `set_state`

Promotes a value from `action_input` (or anywhere in shared state via dot-notation) to a named top-level key — no LLM call.

```yaml
store_task:
  type: set_state
  key: current_task           # write target in shared state
  source: action_input.task   # read path (default: action_input.<leaf of key>)
  merge: true                 # for dicts: merge into existing (default true)
  transitions:
    set: next_block     # value was non-empty
    empty: fallback     # value was None/""/[]/{}
    error: handle_err   # source path missing (optional; raises if omitted)
```

**Forbidden write targets for `set_state`:** `logger`, `tool_context`, `agent_config`, `messages`, `iteration`, `block_visits`, `max_iterations`, `session_id`, `agent_id`, `logs_dir`, and any `_`-prefixed key.

---

## Flow YAML Structure

```yaml
id: my_flow               # must match filename stem
max_iterations: 30        # per-flow cap; agent cap takes precedence if lower
start: think              # first block to enter

on_error:                 # optional error handling — restart at a specific block
  max_iterations:
    start: done
  unhandled:
    start: done

blocks:
  think:
    type: llm
    ...
    transitions:
      search: search_block
      done: END            # END terminates the flow cleanly
      default: think
```

**Transition rules:**
- `END` terminates the flow cleanly
- Always add `default:` on `llm` and `guardrail` blocks
- Cycles are fine — `think → tool → think` is the standard loop pattern
- Per-block visit cap: add `max_visits: N` to a block config to limit re-entries

---

## Agent YAML Structure

```yaml
id: analyst               # must match filename stem; used as --agent arg
name: Analyst             # display name

description: |
  What this agent does, what it owns, when it's invoked.

flows:
  main: analyst_loop      # key = flow alias, value = flows/<value>.yaml stem
  inbox: analyst_loop     # optional: triggers when a mailbox message arrives

max_iterations: 20

model_defaults:
  provider: bedrock
  model_id: us.anthropic.claude-sonnet-4-5-20250929-v1:0

permissions:
  workspace_paths:        # session-scoped scratch: <path>/<session_id>/ is auto-created
    - data/workspace/analyst/
  write_paths:            # stable writable dirs (NOT session-scoped)
    - data/outputs/analyst/
  read_paths:             # read-only source dirs
    - data/shared_knowledge/
  allowed_commands: []    # executables run_command may use; empty = none

memory:
  realms:
    - knowledge_base

guardrails:               # optional: override default input/output safety prompts
  input: |                # custom system prompt for input safety checks
    You are an input safety reviewer...
  output: |               # custom system prompt for output safety checks
    You are an output safety reviewer...

context_files:            # injected verbatim into every LLM block system prompt
  - glob: "shared_knowledge/company/**/*.md"
    tag: "company_info"   # wraps content in <company_info>…</company_info>
```

**Guardrail rules:**
- If `guardrails.input` is present, it overrides `config/guardrails.yaml`'s `input_safety` prompt for this agent.
- If `guardrails.output` is present, it overrides the `output_safety` prompt.
- If either is absent, the system default is used.

**Path rules:**
- Paths starting with `data/` are rewritten to `DATA_DIR/<suffix>` at runtime
- `workspace_paths` are session-scoped: `<path>/<session_id>/` is auto-created so concurrent runs never collide
- `write_paths` are stable directories pre-created at startup
- File tools enforce these paths — any access outside them raises `PermissionError`

### Context Files

`context_files` inject documentation directly into every LLM block's system prompt. This is useful for:
- **System architecture context**: e.g., `docs/project-onboarding.md` for agents that need to understand the system's structure
- **Coding conventions and patterns**: e.g., `docs/how-to-create-agents.md` for agents that create other agents
- **Agent-specific guidance**: instructions that are always relevant to this agent's role

Example:
```yaml
context_files:
  - glob: "docs/project-onboarding.md"
    tag: "system_overview"   # content wrapped in <system_overview>...</system_overview>
  - glob: "docs/how-to-create-agents.md"
    tag: "agent_creation_guide"
```

The `tag` is optional and wraps the content in XML-like tags in the prompt. Multiple `glob` patterns can be specified. Content is injected verbatim (no processing).

**When to use:**
- The Agent Creator has `project-onboarding.md` in context_files to know the stack and directory structure when designing new agents.
- Use context_files for information that is always relevant to the agent's work, regardless of the specific task.
- Don't use context_files for task-specific information — use the conversation or memory instead.

---

## Template Variables in System Prompts

System prompts support Mustache syntax resolved dynamically each block execution.

```yaml
system_prompt: |
  You are {{state.agent_id}}.
  Current task: {{state.current_task}}
  Schedule: {{config.schedules.daily_run_time}}

  Todo list:
  {{#state.todo_list}}
  - {{.}}
  {{/state.todo_list}}

  Writable directories:
  {{#state.write_paths}}- {{.}}
  {{/state.write_paths}}
```

| Syntax | Source |
|---|---|
| `{{state.key}}` | `shared` dict (dot-notation for nested) |
| `{{config.file.key}}` | `config/<file>.yaml` keyed by stem then YAML path |

Protected keys never exposed to templates: `logger`, `tool_context`, `agent_config`, and any `_`-prefixed key.

---

## Tools

### Writing a New Tool

1. Create (or add to) a `*.py` file in `tools/`. It is auto-imported at startup.
2. Decorate the function with `@tool`.
3. Last parameter must be `context: ToolContext`. It is stripped from the Bedrock schema.
4. Type-annotate all non-context parameters. Annotations build the JSON schema.
5. Return a `str`. Return `dict` only if JSON output is intentional.
6. Write a specific docstring — the LLM uses it to decide when and how to call the tool.

```python
from tools import ToolContext, tool

@tool
def get_exchange_rate(from_currency: str, to_currency: str, context: ToolContext) -> str:
    """Return the current exchange rate between two ISO currency codes.
    from_currency: ISO 4217 code, e.g. 'USD'.
    to_currency: ISO 4217 code, e.g. 'EUR'.
    """
    # import heavy dependencies inside the function to avoid slow startup
    import requests
    rate = _fetch_rate(from_currency, to_currency)
    return f"1 {from_currency} = {rate} {to_currency}"
```

### Using a Tool in a Flow

1. List it in the `tools:` section of an `llm` block (so the LLM knows about it).
2. Add a `tool_call` block to execute it.
3. Add a transition from the `llm` block to the `tool_call` block.

```yaml
think:
  type: llm
  tools:
    - get_exchange_rate
  transitions:
    get_exchange_rate: rate_block
    done: END
    default: think

rate_block:
  type: tool_call
  tool: get_exchange_rate
  transitions:
    default: think
```

### Path Safety in Tools

Use `_assert_path_allowed` from `file_tools` to enforce workspace restrictions:

```python
from tools.file_tools import _assert_path_allowed

@tool
def write_report(path: str, content: str, context: ToolContext) -> str:
    """Write a report file inside the agent's allowed workspace."""
    resolved = _assert_path_allowed(path, context)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return f"Written: {path}"
```

### Built-in Tools Reference

| Tool | Module | What it does |
|---|---|---|
| `read_file` | `file_tools` | Read a text file (UTF-8 + latin-1 fallback) |
| `write_file` | `file_tools` | Write/overwrite a file, creates parent dirs |
| `list_files` | `file_tools` | Recursive directory listing |
| `delete_file` | `file_tools` | Delete a file |
| `file_exists` | `file_tools` | Returns `"true"` / `"false"` |
| `store_memory` | `memory_tools` | Store text in ChromaDB with topic+realm |
| `search_memory` | `memory_tools` | Semantic search across all memory |
| `update_memory` | `memory_tools` | Update a memory entry by ID |
| `delete_memory` | `memory_tools` | Delete a memory entry by ID |
| `spawn_agent` | `agent_tools` | Run a sub-agent synchronously, return its output |
| `send_message` | `agent_tools` | Send async message to another agent's mailbox |
| `check_inbox` | `message_tools` | Read this agent's pending mailbox messages |
| `mark_message_processed` | `message_tools` | Move a message to processed |
| `run_command` | `command_tools` | Run a shell command (allowlisted executables only) |
| `schedule_agent` | `schedule_tools` | Create a scheduled/recurring agent run |
| `cancel_schedule` | `schedule_tools` | Remove a schedule |
| `list_schedules` | `schedule_tools` | Show all defined schedules |

---

## Common Flow Patterns

### Pattern 1 — Think/Act Loop (most common)

The agent loops between an LLM decision block and tool execution until it decides it is done.

```yaml
think:
  type: llm
  tools: [search_memory, read_file, write_file]
  transitions:
    search_memory: search_block
    read_file: read_block
    write_file: write_block
    done: END
    default: think

search_block:
  type: tool_call
  tool: search_memory
  transitions:
    default: think

read_block:
  type: tool_call
  tool: read_file
  transitions:
    default: think

write_block:
  type: tool_call
  tool: write_file
  transitions:
    default: guard

guard:
  type: guardrail
  model_id: us.amazon.nova-lite-v1:0
  system_prompt: |
    Review the file write for safety issues.
    ```yaml
    verdict: approved | rejected
    reason: "..."
    ```
  transitions:
    approved: think
    rejected: think
    default: think
```

### Pattern 2 — Classify then Route

Determine intent, then branch to specialised blocks.

```yaml
classify:
  type: llm
  transitions:
    research_task: research_block
    write_task: write_block
    done: END
    default: classify

research_block:
  type: tool_call
  tool: search_memory
  transitions:
    default: think

write_block:
  type: tool_call
  tool: write_file
  transitions:
    default: think
```

### Pattern 3 — Store State, Then Act

Use `set_state` to promote an LLM decision into a named shared variable, then reference it in later prompts via `{{state.current_task}}`.

```yaml
decide:
  type: llm
  system_prompt: |
    Choose the next task.
    ```yaml
    action: assign_task
    action_input:
      current_task: "description of task"
    ```
  transitions:
    assign_task: store_task
    default: decide

store_task:
  type: set_state
  key: current_task
  transitions:
    set: execute
    empty: decide

execute:
  type: llm
  system_prompt: |
    Execute this task: {{state.current_task}}
    ...
```

### Pattern 4 — Sub-agent Delegation

Spawn a sub-agent synchronously (blocking) or fire-and-forget.

```yaml
# Synchronous — parent waits for result
delegate:
  type: tool_call
  tool: spawn_agent
  # action_input must contain: target_agent, prompt
  transitions:
    default: think

# Async — parent continues immediately; target agent's inbox flow handles it
fire_and_forget:
  type: tool_call
  tool: send_message
  transitions:
    default: think
```

---

## Agent Communication

| Method | Tool | Behaviour |
|---|---|---|
| Synchronous | `spawn_agent` | Blocks until sub-agent finishes; returns last assistant message |
| Asynchronous | `send_message` | Writes to target agent's inbox; returns immediately |

For `send_message` to work:
- Target agent must have an `inbox:` flow in its YAML
- Daemon must be running: `uv run run.py --daemon`

---

## Iteration Limits and Error Handling

Two independent guards prevent infinite loops:

1. **Session-level**: `max_iterations` (lowest of agent and flow caps). Each block visit increments `shared["iteration"]`.
2. **Per-block**: `max_visits: N` in a block config limits re-entries for that specific block.

At ~10 turns before the cap, a `[SYSTEM]` warning is injected into the conversation. At the cap, the agent gets 3 grace turns to finalise output, then `MaxIterationsError` is raised.

Use `on_error:` in the flow YAML to define a recovery block:

```yaml
on_error:
  max_iterations:
    start: done   # block id to jump to on MaxIterationsError
  unhandled:
    start: done
```

---

## Data / Path Conventions

- All mutable state lives under `data/` (or `COUNCIL_DATA_DIR` if set)
- Agent YAMLs should use `data/...` paths in `permissions:` — they are rewritten to `DATA_DIR` at runtime
- Never hardcode absolute paths in agent YAMLs or system prompts — use template variables instead:

```yaml
system_prompt: |
  Write output files to:
  {{#state.write_paths}}- {{.}}
  {{/state.write_paths}}
```

- Files/dirs with names starting with `_` or `.` are private/system and are blocked by file tools

---

## Coding Standards (Python)

Follow PEP 8. Key conventions used in this codebase:

- **Type hints**: annotate all function parameters and return types
- **Docstrings**: every public function and class gets a docstring (PEP 257)
- **Imports**: stdlib first, then third-party, then local; heavy deps (boto3, requests) imported inside functions to avoid slow startup
- **`from __future__ import annotations`** at the top of every engine/tools module
- **Error handling**: tools return `"[ERROR] ..."` strings rather than raising — the LLM sees the error and can recover. Raise only for programming errors.
- **Module-level logger**: `_log = logging.getLogger(__name__)` — use `_` prefix for module-private names
- **No global mutable state** outside of the tool registry (`_REGISTRY` in `tools/__init__.py`)

---

## Adding a New Agent — Checklist

1. Create `agents/<id>.yaml` with at minimum `id`, `name`, `flows.main`, `model_defaults`, `permissions`
2. Create `flows/<flow_id>.yaml` referenced by `flows.main`
3. If the agent needs inbox support: add `flows.inbox:` and ensure the daemon is running
4. If the agent needs a new tool: create `tools/<module>.py` with `@tool` functions
5. Test: `uv run run.py --agent <id> --prompt "test prompt"`
6. Check trace: `data/logs/<id>/<session_id>.jsonl`

---

## Adding a New Tool — Checklist

1. Add a `@tool` function to a file in `tools/` (new or existing module)
2. Last parameter must be `context: ToolContext`
3. Type-annotate all non-context params
4. Return `str`
5. Write a descriptive docstring — this is what the LLM reads
6. If the tool touches files, call `_assert_path_allowed(path, context)` first
7. Reference the tool in the relevant flow YAML block's `tools:` list
8. Add a `tool_call` block and a transition to reach it
9. Test the function directly: `from tools.my_module import my_tool; my_tool(..., context=ToolContext(agent_id="test", session_id="test", allowed_paths=["./tmp/"]))`

---

## Testing

```bash
# Run all tests
uv run pytest tests/

# Run a specific test file
uv run pytest tests/test_guardrails.py -v

# Run with output
uv run pytest tests/ -s
```

Tests live in `tests/`. Use real `ToolContext` instances with temporary directories. The `@tool` decorator is transparent — call functions directly for unit tests.

---

## Logs and Debugging

Every session writes a JSONL trace to `data/logs/<agent_id>/<session_id>.jsonl`.

Each line is a JSON object with an `event` field:
- `session_start` / `session_end`
- `block_enter` — fired on entry to every block
- `llm_call` — model, tokens, action, raw response (first 2000 chars)
- `tool_call` — tool name, duration
- `tool_use` — tool name, input, result
- `guardrail` — verdict, reason, tokens
- `transition` — from_block, to_action
- `max_iterations_reached` / `unhandled_error`

To watch a running session:
```bash
tail -f data/logs/<agent_id>/<session_id>.jsonl | python -m json.tool
```

---

## Key Files Quick Reference

| File | Purpose |
|---|---|
| [engine/block.py](engine/block.py) | All block type implementations |
| [engine/flow_loader.py](engine/flow_loader.py) | Parses flow YAML → PocketFlow graph |
| [engine/runner.py](engine/runner.py) | Builds shared state, drives flow execution |
| [engine/template.py](engine/template.py) | Mustache renderer for system prompts |
| [engine/paths.py](engine/paths.py) | All path constants; respects `COUNCIL_DATA_DIR` |
| [engine/state.py](engine/state.py) | Checkpoint save/load |
| [tools/\_\_init\_\_.py](tools/__init__.py) | `@tool` decorator, `ToolContext`, tool registry |
| [tools/file_tools.py](tools/file_tools.py) | File read/write/list/delete + `_assert_path_allowed` |
| [tools/agent_tools.py](tools/agent_tools.py) | `spawn_agent`, `send_message` |
| [pocketflow/\_\_init\_\_.py](pocketflow/__init__.py) | Vendored PocketFlow framework — do not modify |
| [docs/how-to-create-agents.md](docs/how-to-create-agents.md) | Detailed agent creation guide |
| [docs/how-to-add-tools.md](docs/how-to-add-tools.md) | Detailed tool creation guide |
