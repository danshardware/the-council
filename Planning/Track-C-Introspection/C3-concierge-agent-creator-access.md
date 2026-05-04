# C3 — Concierge and Agent Creator Expanded Access

## Overview

Expand the read paths and context files for the Concierge and Agent Creator so they
have the system-level visibility needed to do their jobs.

- **Concierge**: Needs to see session history and workspace state to give informed
  routing decisions and status updates.
- **Agent Creator**: Needs to see past sessions, the tools registry source, and
  existing flow patterns to design good agents.

This is a YAML-only change (agent config files), except for C2's tool additions
which flow through naturally once the tools are registered.

---

## Concierge Changes (`agents/concierge.yaml`)

### Current `read_paths`:

```yaml
read_paths:
  - agents/
  - flows/
  - config/
  - docs/
  - shared_knowledge/
```

### Updated `read_paths`:

```yaml
read_paths:
  - agents/
  - flows/
  - config/
  - docs/
  - data/shared_knowledge/
  - data/logs/
  - data/workspace/
  - data/config/
```

Notes:
- `shared_knowledge/` → changed to `data/shared_knowledge/` (the runtime location).
  Confirm whether the old `shared_knowledge/` was intended — if it pointed to the
  repo root, it may have been wrong.
- `data/logs/` — read session history for context
- `data/workspace/` — see agent workspace state

### Add `list_tools` and `search_tools` to available tools

In `concierge_loop.yaml`, add `list_tools` and `search_tools` to the `route` block's
tools list so the Concierge can check tool availability when advising users.

---

## Agent Creator Changes (`agents/agent_creator.yaml`)

### Current `read_paths`:

```yaml
read_paths:
  - agents/
  - flows/
  - docs/
  - config/
```

### Updated `read_paths`:

```yaml
read_paths:
  - agents/
  - flows/
  - docs/
  - config/
  - tools/              # source of all tool implementations — know what exists
  - data/agents/        # user-created agents (written by agent_creator itself)
  - data/flows/         # user-created flows
  - data/logs/          # past session history for evaluation
  - data/workspace/agent_creator/   # own past work
```

### Updated `context_files`

Add the tools index as a context file so the LLM knows what's available without
having to read every tool file:

```yaml
context_files:
  - glob: "docs/how-to-create-agents.md"
    tag: "agent_creation_guide"
  - glob: "docs/how-to-add-tools.md"
    tag: "tool_creation_guide"
  - glob: "docs/project-onboarding.md"
    tag: "system_overview"         # NEW — system architecture context
```

`project-onboarding.md` has the directory map and stack overview — useful for an
agent that creates other agents.

### Add `list_tools` and `search_tools` to Agent Creator flow

In `agent_creator_loop.yaml`, add `list_tools` and `search_tools` to the planning
and design blocks.  The Agent Creator should call `list_tools` early in every session
to know what's available before proposing tool assignments for a new agent.

---

## Testing Plan (TDD)

File: `tests/test_introspection_access.py`

```python
def test_concierge_can_read_logs():
    """Concierge must be able to list session log files."""
    runner = AgentRunner(agent_id="concierge")
    shared = runner.run(
        prompt="List the most recent session logs for the ops agent."
    )
    messages = [m["content"] for m in shared["messages"] if m["role"] == "assistant"]
    # Should mention log files or session IDs
    assert any("log" in m.lower() or ".jsonl" in m.lower() for m in messages)

def test_agent_creator_can_read_tools_source():
    """Agent Creator must be able to read tools/ source files."""
    runner = AgentRunner(agent_id="agent_creator")
    shared = runner.run(
        prompt="List all available tools and their descriptions."
    )
    messages = [m["content"] for m in shared["messages"] if m["role"] == "assistant"]
    assert any("read_file" in m or "write_file" in m for m in messages)

def test_agent_creator_sees_system_overview_in_context():
    """Agent Creator's context injection should include the system overview."""
    # Load agent config and check context_files includes project-onboarding.md
    import yaml
    with open("agents/agent_creator.yaml") as f:
        cfg = yaml.safe_load(f)
    context_globs = [cf["glob"] for cf in cfg.get("context_files", [])]
    assert any("project-onboarding" in g for g in context_globs)
```

---

## Acceptance Criteria

### Concierge
- [ ] `data/logs/` in `read_paths`
- [ ] `data/workspace/` in `read_paths`
- [ ] `data/config/` in `read_paths`
- [ ] `data/shared_knowledge/` replaces `shared_knowledge/` (verify correct runtime path)
- [ ] `list_tools` and `search_tools` in `concierge_loop.yaml` route block tools

### Agent Creator
- [ ] `tools/` in `read_paths`
- [ ] `data/agents/` and `data/flows/` in `read_paths`
- [ ] `data/logs/` in `read_paths`
- [ ] `data/workspace/agent_creator/` in `read_paths`
- [ ] `docs/project-onboarding.md` added to `context_files`
- [ ] `list_tools` and `search_tools` in `agent_creator_loop.yaml` planning blocks
- [ ] All tests pass

---

## QA Notes

- Verify the `shared_knowledge/` vs `data/shared_knowledge/` distinction.  The
  Concierge currently has `shared_knowledge/` which resolves to the repo root.
  The actual runtime data is at `data/shared_knowledge/`.  This may be an existing
  bug — confirm and fix consistently.
- Agent Creator's `write_paths` (`data/agents/`, `data/flows/`) are unchanged.
- Do NOT give Agent Creator write access to `tools/` — it reads source for context,
  but tool creation requires a human to add to the codebase.

---

## Instructions to the Coder

1. Open `agents/concierge.yaml` — update `read_paths`.
2. Open `agents/agent_creator.yaml` — update `read_paths` and `context_files`.
3. Open `flows/concierge_loop.yaml` — add `list_tools`, `search_tools` to `route`
   block tools list.
4. Open `flows/agent_creator_loop.yaml` — identify the planning/design blocks and
   add `list_tools`, `search_tools` to their tools lists.
5. Run the test suite.
