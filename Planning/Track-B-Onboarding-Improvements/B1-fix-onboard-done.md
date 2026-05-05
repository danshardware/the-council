# B1 — Fix onboard_done Block

## Overview

The `onboard_done` block in `flows/concierge_onboarding.yaml` generates a summary
message but never delivers it to the human — it just ends the flow silently.  Fix it
so the summary is shown to the user before the flow terminates.

---

## Type Contracts

No code changes.  This is a YAML-only fix.

The `onboard_done` block must:
1. Generate the summary (LLM call — already exists)
2. Deliver the summary to the human via a `human_reply` or `human_input` block
3. Then transition to `END`

---

## Current State (broken)

```yaml
onboard_done:
  type: llm
  system_prompt: |
    Onboarding is complete. Write a warm, clear summary including:
    ...
    Respond ONLY with valid YAML:
    ```yaml
    reasoning: "everything is set up"
    action: done
    action_input:
      summary: |
        <your onboarding completion message>
    ```
  transitions:
    done: END         # <-- summary never leaves the LLM block
    default: END
```

The LLM generates `action_input.summary` but nothing sends it to the user.

---

## Workflow

### Fix: Add a `done_send` block after `onboard_done`

Modify the flow so that after `onboard_done` generates its summary:
- It transitions to `onboard_done_send` (a `human_reply` block)
- `human_reply` delivers the summary to the user
- If the channel replies, handle gracefully (usually just END)

```yaml
onboard_done:
  type: llm
  system_prompt: |
    Onboarding is complete. Write a warm, clear summary including:

    - What was set up (mission file written to data/shared_knowledge/company/mission.md).
    - Which agents were created (if any).
    - Channel status.
    - How to invoke agents going forward:
        uv run run.py --agent <id> --prompt "your task"
      Or via the configured Discord channel.
    - How to re-run onboarding if anything needs to change:
        uv run run.py --agent concierge --flow onboarding --prompt "restart onboarding"

    Respond ONLY with valid YAML:
    ```yaml
    reasoning: "everything is set up"
    action: send_summary
    action_input:
      message: |
        <your onboarding completion message — friendly, well-formatted Markdown>
    ```
  transitions:
    send_summary: onboard_done_send
    default: onboard_done_send

onboard_done_send:
  type: human_reply
  transitions:
    replied: END
    default: END
```

### How `human_reply` delivers the message

The `human_reply` block reads `shared["action_input"]["message"]` (set by the
preceding LLM block) and surfaces it via the active channel adapter
(Discord embed, CLI print, etc.).  Confirm this is how `HumanReplyBlock` works
before finalising — if it uses a different key, adjust accordingly.

---

## Testing Plan (TDD)

File: `tests/test_onboarding_flow.py` (extend existing or create new)

```python
def test_onboard_done_delivers_message():
    """
    Run the onboarding flow end-to-end (simulate an already-onboarded system
    to skip the interview) and assert the summary reaches the output.
    """
    # Pre-create mission.md so onboarding routes to already_done path.
    # Run concierge with flow=onboarding.
    # Assert: shared["messages"] contains an assistant message with onboarding
    # completion language ("set up", "agents", etc.)
    runner = AgentRunner(agent_id="concierge")
    shared = runner.run(prompt="Begin onboarding.", flow_name="onboarding")
    messages = [m for m in shared.get("messages", []) if m["role"] == "assistant"]
    assert any(
        "set up" in m["content"].lower() or "onboarding" in m["content"].lower()
        for m in messages
    )
```

---

## Acceptance Criteria

- [ ] `onboard_done` block transitions to a `human_reply` block, not directly to `END`
- [ ] The human_reply block uses `action_input.message` from the preceding LLM output
- [ ] Running the flow leaves at least one assistant message in `shared["messages"]`
      containing the summary
- [ ] Flow terminates cleanly after delivery (no hanging blocks)
- [ ] `on_error` handlers still work (they route to `onboard_done` — confirm summary
      still delivered even on error path)

---

## QA Notes

- Check how `HumanReplyBlock` is implemented in `engine/block.py` — specifically
  which key it reads for the message to send (`action_input.message` is the
  convention used elsewhere, but verify).
- The `on_error` handlers both route to `onboard_done` — that's fine, the fix makes
  the error path also deliver a message, which is better than silent failure.
- This is a YAML-only change.  Do not touch `block.py`.

---

## Instructions to the Coder

1. Open `flows/concierge_onboarding.yaml`.
2. Modify `onboard_done` to transition to `send_summary: onboard_done_send` instead
   of `done: END`.
3. Add `onboard_done_send` as a `human_reply` block with `transitions: replied: END, default: END`.
4. Verify the HumanReplyBlock implementation in `block.py` to confirm the message key.
5. Run the test.
