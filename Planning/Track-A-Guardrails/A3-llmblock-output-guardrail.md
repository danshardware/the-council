# A3 — LLMBlock Output Guardrail

## Overview

After every LLM block produces a response (action + reasoning + action_input),
run an output safety check before the transition fires.

- `approved` → transition proceeds normally
- `warn` → inject a `[SYSTEM]` warning into the conversation (LLM sees it next turn),
  transition still proceeds so the agent can self-correct on the next step
- `rejected` → inject a `[SYSTEM]` message, override the transition to `"default"` so
  the LLM must retry from the same block with corrective context

This is wired into `LLMBlock.post()` in `engine/block.py`.

---

## Type Contracts

### New private function in `block.py`:

```python
def _run_output_guardrail(
    shared: dict,
    action: str,
    reasoning: str,
    action_input: dict,
    guardrail_prompt: str,
    model_id: str = "us.amazon.nova-lite-v1:0",
) -> str:
    """
    Run the output safety guardrail.

    Returns the effective action string:
    - On approved/warn: returns `action` unchanged
    - On rejected: returns "default" (forces LLM to retry same block)

    Side-effects:
    - On warn: injects a [SYSTEM] advisory into shared["messages"] / live conv
    - On rejected: injects a [SYSTEM] rejection notice into shared["messages"] / live conv
    """
```

### Message format injected into conversation:

```python
# warn
"[SYSTEM] Output advisory: {reason}. Review your proposed action before proceeding."

# rejected
"[SYSTEM] Your proposed action '{action}' was blocked. Reason: {reason}. "
"Reconsider and propose a different action."
```

---

## Workflow

### Step 1 — Load guardrail prompt in `LLMBlock.post()`

```python
def post(self, shared: dict, prep_res: dict, exec_res: dict) -> str:
    action = exec_res.get("action", "default")
    ...  # existing shared updates

    # === OUTPUT GUARDRAIL ===
    _output_prompt = (
        shared.get("_output_guardrail_prompt")  # set by runner from agent YAML (A5)
        or ""
    )
    if _output_prompt:
        action = _run_output_guardrail(
            shared=shared,
            action=action,
            reasoning=shared.get("reasoning", ""),
            action_input=shared.get("action_input", {}),
            guardrail_prompt=_output_prompt,
        )
    # ========================

    return action
```

### Step 2 — Runner sets `_output_guardrail_prompt` in shared

In `runner.py`, when building the `shared` dict (same place as A2):

```python
from engine.template import _load_config_dir
_guardrail_cfg = _load_config_dir().get("guardrails", {})
shared["_output_guardrail_prompt"] = (
    agent_config.get("guardrails", {}).get("output")   # per-agent override (A5)
    or _guardrail_cfg.get("output_safety", "")
)
```

This is a private key (prefixed with `_`) so it is never forwarded to the LLM in
system prompts and is stripped from state context by the template engine.

### Step 3 — Inside `_run_output_guardrail()`

```python
import yaml as _yaml
from engine.llm import call_llm

user_msg = (
    f"Proposed action: {action}\n"
    f"Reasoning: {reasoning[:400]}\n"
    f"Action input:\n{_yaml.dump(action_input, default_flow_style=False)[:400]}"
)

parsed, _, _ = call_llm(
    model_id=model_id,
    system_prompt=guardrail_prompt,
    messages=[{"role": "user", "content": user_msg}],
)
verdict = parsed.get("verdict", "approved")
reason = parsed.get("reason", "")

if verdict == "rejected":
    _push_message(
        shared, "user",
        f"[SYSTEM] Your proposed action '{action}' was blocked. "
        f"Reason: {reason}. Reconsider and propose a different action."
    )
    return "default"

if verdict == "warn":
    _push_message(
        shared, "user",
        f"[SYSTEM] Output advisory: {reason}. "
        "Review your proposed action before proceeding."
    )

return action  # approved or warned-but-continuing
```

### Step 4 — Log the result

Add a log event inside `_run_output_guardrail()`:

```python
logger = shared.get("logger")
if logger:
    logger.log_event(
        shared,
        "output_guardrail",
        action=action,
        verdict=verdict,
        reason=reason,
    )
```

---

## Important: Skip on GuardrailBlock transitions

The output guardrail should NOT run when the current block is itself a `GuardrailBlock`
or a `ToolCallBlock` — only on `LLMBlock`.  Since this logic lives in `LLMBlock.post()`,
this is already ensured by design.

---

## Testing Plan (TDD)

File: `tests/test_llmblock_output_guardrail.py`

Write tests BEFORE implementing.

```python
def test_approved_action_passes_through():
    """A normal write_file action must transition unchanged."""
    # Run a one-shot agent session with a benign prompt.
    # Assert the flow completed normally (iteration > 0, no [SYSTEM] injected).
    ...

def test_rejected_action_retries_block():
    """A clearly injected action must not proceed — action becomes 'default'."""
    # Craft a scenario where the LLM is likely to produce a suspicious action.
    # Assert: [SYSTEM] rejection message appears in messages.
    # Assert: the block was visited at least twice (retry happened).
    ...

def test_warn_action_gets_advisory():
    """A marginally suspicious action gets an advisory but still proceeds."""
    # Assert: [SYSTEM] advisory appears in messages.
    # Assert: flow continued (did not stay on same block forever).
    ...

def test_output_guardrail_not_run_when_prompt_empty():
    """If _output_guardrail_prompt is empty, no guardrail runs."""
    # Set shared["_output_guardrail_prompt"] = "".
    # Assert: no output_guardrail event in logger.
    ...

def test_output_guardrail_uses_cheap_model():
    """Guardrail must use Nova Lite, not the agent's main model."""
    # Spy on call_llm calls; assert model_id == "us.amazon.nova-lite-v1:0"
    # when originating from _run_output_guardrail.
    ...
```

---

## Acceptance Criteria

- [ ] `_run_output_guardrail()` is a module-level private function in `block.py`
- [ ] Called from `LLMBlock.post()` only when `shared["_output_guardrail_prompt"]` is non-empty
- [ ] `rejected` → action becomes `"default"`, `[SYSTEM]` message injected
- [ ] `warn` → action unchanged, `[SYSTEM]` advisory injected
- [ ] `approved` → action unchanged, no message injected
- [ ] Always uses `us.amazon.nova-lite-v1:0`
- [ ] Result is logged as `"output_guardrail"` event
- [ ] `_output_guardrail_prompt` key is private (starts with `_`) and never appears in
      system prompts or tool calls
- [ ] Does not run during `GuardrailBlock` or `ToolCallBlock` execution

---

## QA Notes

- The `"default"` transition causes the same LLMBlock to be revisited (if the block
  has no explicit `default:` override).  This is intentional — the injected [SYSTEM]
  message gives the LLM a chance to self-correct.
- The `max_visits` per-block cap still applies — a persistent rejection loop will
  eventually hit `MaxIterationsError` and be caught by `on_error`.
- Do not truncate the action_input passed to the guardrail — but do cap it at ~400 chars
  to control cost.  The guardrail needs enough context to make a decision.
- The guardrail runs synchronously inside `post()`.  It adds one Nova Lite call per
  LLM block transition.  This is intentional and cheap.

---

## Instructions to the Coder

1. Complete A1 (prompts) and A2 (input guardrail) first.
2. Open `engine/block.py`.
3. Add `_run_output_guardrail()` as a module-level private function, near `_push_message`.
4. In `LLMBlock.post()`, after the existing `shared["action"] = action` line, add the
   guardrail call.  Make sure the final `return action` returns the (possibly overridden)
   action from `_run_output_guardrail`.
5. Open `engine/runner.py`.  In the `shared` dict construction, add
   `"_output_guardrail_prompt": ...` using the same resolution logic as the input prompt.
6. Run tests.
