# How to create an agent

## Minimum required files

1. `agents/<id>.yaml` — agent definition
2. `flows/<flow_id>.yaml` — at least one flow (the `main` flow)

No Python code is needed for a new agent unless it uses a new tool.

---

## Agent YAML (`agents/<id>.yaml`)

```yaml
id: analyst                          # must match filename stem
name: Analyst                        # display name (used in logs/UI)
description: |
  One paragraph. What this agent does, what it owns, when it's invoked.

flows:
  main: analyst_loop                 # key = flow alias, value = flows/<value>.yaml stem
  inbox: analyst_loop                # optional: inbox flow (triggered by mailbox messages)

max_iterations: 20                   # hard cap across all blocks in a session

model_defaults:
  provider: bedrock
  model_id: us.anthropic.claude-sonnet-4-5-20250929-v1:0

permissions:
  workspace_paths:
    - workspace/analyst/             # agent can only read/write here via file tools
  allowed_commands: []               # executables run_command may use; empty = no commands

memory:
  realms:
    - knowledge_base                 # which ChromaDB realms this agent can access
    - institutional                  # valid values: knowledge_base | institutional | sop

context_files:                       # files injected into every LLM system prompt
  - glob: "shared_knowledge/company/**/*.md"
    tag: "company_info"              # becomes <company_info>…</company_info> in system prompt
```

**Fields:**
- `id` — must be unique, matches filename stem, used as `--agent` CLI arg and for mailbox routing
- `flows` — at minimum provide `main`; add `inbox` if the agent should react to mailbox messages
- `max_iterations` — combined with the flow's own cap; the lower wins
- `permissions.workspace_paths` — file tools enforce these; agent cannot escape them
- `permissions.allowed_commands` — `run_command` blocks any executable not in this list
- `memory.realms` — not currently enforced at query time but documents intent
- `context_files` — each entry glob-expands at session start; files are read, wrapped in XML tags, prepended to every `llm` block's system prompt in that session

---

## Flow YAML (`flows/<flow_id>.yaml`)

```yaml
id: analyst_loop
max_iterations: 30                   # per-flow cap (agent cap takes precedence if lower)
start: think                         # first block to enter

blocks:

  think:
    type: llm
    model_id: us.anthropic.claude-sonnet-4-5-20250929-v1:0   # omit to use agent default
    system_prompt: |
      You are an analyst. Decide what to do next.

      Respond ONLY with valid YAML:
      ```yaml
      reasoning: "your thinking"
      action: search_memory   # search_memory | write_report | done
      action_input:
        query: "search terms"   # fields vary by action
      ```
    tools:
      - search_memory            # tools listed here appear in the system prompt schema
      - read_file
    transitions:
      search_memory: search_block
      write_report: write_block
      done: END
      default: think             # fallback if LLM returns an unrecognised action

  search_block:
    type: tool_call
    tool: search_memory          # must match a registered tool name
    transitions:
      default: think

  write_block:
    type: tool_call
    tool: write_file
    transitions:
      default: guard_block

  guard_block:
    type: guardrail
    model_id: us.amazon.nova-lite-v1:0
    system_prompt: |
      Review the last file write for safety concerns.
      Respond ONLY:
      ```yaml
      verdict: approved   # approved | flagged
      reason: "brief"
      ```
    transitions:
      approved: think
      flagged: think
      default: think
```

---

## Block types reference

### `llm`
Calls Bedrock, injects system prompt + tool schemas, appends response to `messages`, parses YAML action from response, returns action string.

```yaml
type: llm
model_id: ...          # optional; inherits agent default if absent
system_prompt: |       # required; context_files and tool schemas are auto-prepended
  ...
tools:                 # optional; list of registered tool names to expose
  - search_memory
transitions:
  <action>: <block_id>
  default: <block_id>  # include this; used when LLM returns an unrecognised action
```

**System prompt conventions:**
- Tell the agent exactly what YAML format to respond in
- List every valid action string in a comment
- The framework auto-appends tool signatures and workspace paths — don't duplicate them

### `guardrail`
Same as `llm` but shown with a shield icon. Designed to review and return `approved`, `needs_confirmation`, or `rejected`/`flagged`.

```yaml
type: guardrail
model_id: us.amazon.nova-lite-v1:0   # use a cheap model
system_prompt: |
  Review ... Respond ONLY:
  ```yaml
  verdict: approved   # approved | needs_confirmation | rejected
  reason: "..."
  ```
transitions:
  approved: next_block
  needs_confirmation: human_checkpoint
  rejected: some_block
  default: some_block
```

### `tool_call`
Calls one registered tool. Reads the last `action_input` dict from `shared` (set by the preceding LLM block), calls the tool, appends result to `messages`.

```yaml
type: tool_call
tool: write_file       # must match a @tool function name
transitions:
  default: next_block
```

### `checkpoint`
Saves the entire session state to `workspace/<agent_id>/checkpoints/<session_id>.json` then raises `SuspendExecution`. The agent halts; it can be resumed via `AgentRunner.resume()`.

```yaml
type: checkpoint
transitions:
  default: next_block   # followed after resume
```

### `human_input`
Prints a prompt to stdout, reads one line from stdin. Maps `y`/`yes` → `approved`, anything else → `rejected`.

```yaml
type: human_input
prompt: "Approve this action? [y/n]: "
transitions:
  approved: next_block
  rejected: fallback_block
```

---

## Transitions and control flow

- Transitions map action strings (returned by the block) to the next block ID
- `END` as a target causes the flow to terminate cleanly
- A `default:` transition catches any action the LLM returns that isn't explicitly mapped
- Always include `default:` on `llm` and `guardrail` blocks; if missing, an unexpected LLM output will terminate the flow silently
- Cycles are fine — e.g., `think → tool_call → think` is the standard research loop

---

## Iteration guards

Two independent guards prevent infinite loops:
1. **Session-level**: `max_iterations` (lowest of agent and flow caps). Each block visit increments the counter.
2. **Per-block**: `max_visits: N` in a block's config limits how many times that specific block can fire in a session.

Both raise `MaxIterationsError` which the runner catches and logs.

---

## Testing a new agent

Run it directly with a short prompt. Check the trace log at `logs/<agent_id>/<session_id>.jsonl`.

```bash
uv run run.py --agent analyst --prompt "Summarise what products we sell"
```

For quick iteration, use a cheaper model (`nova-lite`) in the `think` block while building the flow, then switch to Sonnet/Opus once the logic is right.

---

## Agent communication

**Synchronous (blocking):** Use `spawn_agent` tool. The calling agent blocks until the sub-agent completes. Good for tasks where you need the answer immediately.

**Asynchronous (fire-and-forget):** Use `send_message` tool. The message is written to the target agent's inbox. The daemon picks it up and triggers the target agent's `inbox` flow. Good for tasks that can run in parallel.

For `send_message` to work, the target agent needs an `inbox:` flow defined in its YAML, and the daemon must be running (`uv run run.py --daemon`).

---

## Shared knowledge

Files placed under `shared_knowledge/` can be auto-injected into an agent's system prompts via `context_files:` in the agent YAML. They are not searched — they are prepended verbatim (wrapped in XML tags) to every LLM block call in the session. Keep them concise. Long files slow down every call and consume token budget.
