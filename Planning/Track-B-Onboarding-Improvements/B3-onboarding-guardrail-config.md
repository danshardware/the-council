# B3 — Onboarding Guardrail Config Step

## Overview

After the mission file is written, offer the user a single optional question about
content restrictions.  If they answer, Ops writes `data/config/company_info.yaml`
which the `content_safety` guardrail prompt (B4) picks up via template substitution.

This step is **opt-in** — if the user says "nothing specific" or skips, onboarding
continues with B4's default ("not configured — run onboarding") prompt.

---

## Type Contracts

No code changes.  This is a YAML-only change to `flows/concierge_onboarding.yaml`.

### New `data/config/company_info.yaml` schema (written by Ops via spawn_agent):

```yaml
name: "Acme Corp"                     # company name (from mission interview)
description: "B2B SaaS for HR"        # one-line description
restricted_topics:                    # optional — topics always off-limits
  - "competitor disparagement"
  - "financial advice without disclaimer"
```

---

## Workflow

### New block: `guardrail_config` — after `write_mission`, before `agent_setup`

The Concierge asks a single optional question about off-limits topics, then
delegates to Ops to write `data/config/company_info.yaml`.

```yaml
guardrail_config:
  type: llm
  system_prompt: |
    The mission file has been written.

    Ask the human one simple question:
    "Are there any specific topics that should always be off-limits for the
    Council's AI agents? (e.g. competitor names, regulated industries, internal
    project codenames.) If not, just say 'nothing specific' and we'll use sensible
    defaults."

    If the human provides restrictions → respond with action: delegate_to_ops,
    passing an instruction to write data/config/company_info.yaml with:
      - name: <company name from mission>
      - description: <one-line description from mission>
      - restricted_topics: [<list from human>]

    If the human says nothing specific or skips → respond with action: agent_setup.

    Respond ONLY with valid YAML:
    ```yaml
    reasoning: "what the human said and whether to delegate"
    action: ask_human | delegate_to_ops | agent_setup
    action_input:
      # for ask_human: message
      # for delegate_to_ops: instruction (what to write and where)
    ```
  tools:
    - spawn_agent
  transitions:
    ask_human: guardrail_config_ask
    delegate_to_ops: guardrail_config_ops
    agent_setup: agent_setup
    default: agent_setup

guardrail_config_ask:
  type: human_reply
  transitions:
    replied: guardrail_config
    default: guardrail_config_human_input

guardrail_config_human_input:
  type: human_input
  prompt: "Are there any topics that should always be off-limits?"
  transitions:
    approved: guardrail_config
    rejected: agent_setup
    default: agent_setup

guardrail_config_ops:
  type: tool_call
  tool: spawn_agent
  transitions:
    default: agent_setup
```

### Flow order change

Update `write_mission` block's `agent_setup` transition to go to `guardrail_config`
instead:

```yaml
# In write_mission block:
transitions:
  write_file: mission_write_block
  agent_setup: guardrail_config    # was: agent_setup
  default: guardrail_config        # was: agent_setup
```

---

## Role of Concierge vs. Ops

The Concierge **asks the question and delegates** — it does not write the file itself.
`spawn_agent("ops", "Write data/config/company_info.yaml with: name=..., description=...,
restricted_topics=[...]")` is the correct pattern.

The Concierge's `write_paths` do NOT include `data/config/` and must not be expanded
for this task.

---

## Testing Plan (TDD)

File: `tests/test_onboarding_guardrail_config.py`

```python
def test_guardrail_config_step_is_skippable():
    """
    If the user skips the restrictions question, onboarding continues normally
    and no company_info.yaml is written.
    """
    # Run onboarding flow with canned responses that skip the restrictions step.
    # Assert: data/config/company_info.yaml does NOT exist after the session.
    ...

def test_guardrail_config_writes_file_when_restrictions_given():
    """
    If the user provides restrictions, Ops writes company_info.yaml.
    """
    # Run onboarding flow with canned responses that include restrictions.
    # Assert: data/config/company_info.yaml exists with the expected content.
    ...
```

(These are integration tests that require real AWS and a running Ops agent.)

---

## Acceptance Criteria

- [ ] New `guardrail_config` block exists in `concierge_onboarding.yaml`
- [ ] Block appears after `write_mission`, before `agent_setup`
- [ ] User can skip with "nothing specific" → goes straight to `agent_setup`
- [ ] User providing restrictions → Ops spawned → `data/config/company_info.yaml` written
- [ ] Concierge does NOT write the file itself
- [ ] `company_info.yaml` follows the schema above
- [ ] `on_error` handlers still route to `onboard_done` (no change needed)

---

## QA Notes

- The Concierge should not ask repeatedly if the user says nothing.  One question,
  one shot — any non-specific answer continues to `agent_setup`.
- The `spawn_agent` tool call is synchronous — Ops will run and complete before
  onboarding continues.  This is correct.
- `data/config/` is already in Ops' `write_paths`, so this requires no permission change.

---

## Instructions to the Coder

1. Open `flows/concierge_onboarding.yaml`.
2. Add the four new blocks after `write_mission`.
3. Update `write_mission`'s `agent_setup` transition to `guardrail_config`.
4. Run tests.
