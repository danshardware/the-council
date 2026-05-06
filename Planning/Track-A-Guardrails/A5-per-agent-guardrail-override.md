# A5 — Per-Agent Guardrail Override

## Overview

Allow individual agents to substitute their own guardrail prompts instead of the
system defaults.  Agents can replace (not disable) either or both of `input` and
`output`.  This is declared in the agent YAML.

---

## Type Contracts

### Agent YAML schema addition (optional key):

```yaml
# agents/<id>.yaml
guardrails:
  input: |
    You are a safety reviewer for a highly regulated financial firm...
    <custom input prompt>
  output: |
    You are a safety reviewer checking proposed actions for a financial firm...
    <custom output prompt>
```

Both sub-keys are optional.  If absent, the system default from
`config/guardrails.yaml` is used.  There is no way to set either to empty/null
to disable — an empty string falls back to the system default.

### Runner resolution logic:

```python
def _resolve_guardrail_prompt(
    agent_config: dict,
    key: Literal["input", "output"],
    system_defaults: dict,
) -> str:
    """
    Return the guardrail prompt to use for `key` ("input" or "output").

    Priority:
    1. agent_config["guardrails"][key] if non-empty
    2. system_defaults["input_safety"] / system_defaults["output_safety"]
    3. "" (empty — caller should skip the guardrail check)
    """
    agent_override = (
        agent_config.get("guardrails", {}).get(key, "") or ""
    ).strip()
    if agent_override:
        return agent_override
    fallback_key = "input_safety" if key == "input" else "output_safety"
    return (system_defaults.get(fallback_key, "") or "").strip()
```

Place this in `runner.py` as a module-level private function.

---

## Workflow

### Step 1 — Load system defaults once in `run()`

```python
from engine.template import _load_config_dir
_guardrail_defaults = _load_config_dir().get("guardrails", {})
```

### Step 2 — Resolve both prompts

```python
_input_guardrail_prompt = _resolve_guardrail_prompt(
    agent_config, "input", _guardrail_defaults
)
_output_guardrail_prompt = _resolve_guardrail_prompt(
    agent_config, "output", _guardrail_defaults
)
```

### Step 3 — Store in shared state

```python
shared["_input_guardrail_prompt"] = _input_guardrail_prompt   # used by A2
shared["_output_guardrail_prompt"] = _output_guardrail_prompt  # used by A3
```

### Step 4 — Update A2 and A3 to read from shared

A2's `_check_input_guardrail()` receives the prompt as a parameter (already done).
A3's `LLMBlock.post()` reads `shared["_output_guardrail_prompt"]` (already done in A3 spec).

Ensure A2 also passes `shared["_input_guardrail_prompt"]` rather than re-loading config.

---

## Testing Plan (TDD)

File: `tests/test_per_agent_guardrail_override.py`

```python
def test_agent_override_replaces_default_input_prompt():
    """If agent YAML has guardrails.input, that prompt is used, not system default."""
    # Load an agent that has a custom guardrails.input
    # Spy on call_llm to capture the system_prompt passed to the guardrail
    # Assert system_prompt matches the agent's custom prompt, not input_safety default
    ...

def test_agent_override_replaces_default_output_prompt():
    """If agent YAML has guardrails.output, that prompt is used, not system default."""
    ...

def test_empty_override_falls_back_to_default():
    """If guardrails.input is "" or absent, system default is used."""
    # Create a temp agent config with guardrails: input: ""
    # Assert system default input_safety prompt is used
    ...

def test_resolve_guardrail_prompt_priority():
    """Unit test the resolution function directly."""
    agent_cfg = {"guardrails": {"input": "my custom prompt"}}
    defaults = {"input_safety": "system default"}
    result = _resolve_guardrail_prompt(agent_cfg, "input", defaults)
    assert result == "my custom prompt"

def test_resolve_guardrail_prompt_fallback():
    agent_cfg = {}
    defaults = {"input_safety": "system default"}
    result = _resolve_guardrail_prompt(agent_cfg, "input", defaults)
    assert result == "system default"
```

---

## Acceptance Criteria

- [ ] `_resolve_guardrail_prompt()` exists in `runner.py`
- [ ] Agent YAML `guardrails: input:` and `guardrails: output:` keys are read
- [ ] Non-empty agent override takes priority over system default
- [ ] Empty string or absent key falls back to system default
- [ ] Both prompts stored in shared as private keys (`_input_guardrail_prompt`,
      `_output_guardrail_prompt`)
- [ ] No agent can set either guardrail to empty to disable it — empty always falls
      back to the system default
- [ ] All A5 tests pass

---

## QA Notes

- This task is almost entirely plumbing.  Most of the logic is a 10-line function.
- The tricky edge case is `guardrails: input: null` in YAML — `yaml.safe_load` will
  turn that into Python `None`, which `or ""` handles correctly.
- Do not add agent YAML schema validation in this task — that's a nice-to-have for later.
- The existing agents (concierge, ops, agent_creator, etc.) do NOT need `guardrails:`
  keys yet — the system defaults apply to all of them.

---

## Instructions to the Coder

1. Complete A2 and A3 first — this task reorganises how they receive their prompts.
2. Open `engine/runner.py`.
3. Add `_resolve_guardrail_prompt()` as a module-level private function.
4. In `AgentRunner.run()`, load `_guardrail_defaults` once, resolve both prompts,
   and store them in the `shared` dict (under private `_` keys).
5. Update the `_check_input_guardrail()` call in A2 to read from
   `shared["_input_guardrail_prompt"]` rather than loading config itself.
6. Run the full A test suite (A1–A5) to confirm nothing regressed.
