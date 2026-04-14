# T05: Channel Tools

## File
`tools/channel_tools.py`

## Purpose
Agent-callable tools for sending messages to the originating channel. Agents use these
to post proactive content (briefings, alerts) or reply contextually without going through
the full HumanInputBlock flow.

## Availability gating

Tools in this file are registered as normal `@tool`-decorated functions. However, they
are only added to an agent's tool list when **both** are true:
1. The agent's YAML has `discord.enabled: true` (or omitted, which defaults to `true`).
2. The agent was invoked in a context that has `channel_context` in `shared` — **or** —
   the tool call explicitly provides a `channel_id` (for proactive / bot-initiated posts).

This keeps these tools out of agents that have opted out, without polluting the
existing tool-registration logic. The gating check happens in the tool's body:
if `discord.enabled` is false on the calling agent, the tool raises `PermissionError`
with a clear message.

## Tools

### `send_channel_message(content: str, channel_id: str | None = None) -> str`

Post plain text to the current channel (from `channel_context`) or to an explicit
`channel_id`. Returns `"ok"` on success.

Use case: short acknowledgements, status updates mid-flow.

### `post_channel_embed(title: str, description: str, channel_id: str | None = None) -> str`

Post a rich embed using the agent's name, emoji, and colour from its YAML.
If `channel_id` is given and there is no active `channel_context`, post directly to
that channel (bot-initiated, no thread).
Returns the Discord message ID as a string.

Use case: daily briefings, alert reports, proactive summaries.

### `ask_human(question: str) -> str`

Convenience wrapper:
1. Posts a question embed in the current thread (or creates one).
2. Stores the thread state for reply detection.
3. Returns `"suspended — awaiting human reply"`.

Internally calls `HumanInputBlock`-compatible logic (does not duplicate it — delegates
to `engine/block.py HumanInputBlock._ask_via_channel()`).

## Implementation notes

- All three tools are `async`-compatible but wrapped for the synchronous `ToolCallBlock`
  context. Use `asyncio.run_coroutine_threadsafe(coro, loop)` where `loop` is the
  discord.py event loop stored in `shared["_discord_loop"]` by the gateway.
- If no `_channel_adapter` is in `shared` (agent not running via Discord), all three
  tools raise `RuntimeError("No channel adapter — not running via a channel.")`.
- Tool context: reads `shared["channel_context"]` and `shared["_channel_adapter"]`.

## Acceptance Criteria

- [ ] **AC-01**: `send_channel_message` posts text to the originating thread (in-context).
- [ ] **AC-02**: `post_channel_embed` posts embed directly to a channel when called with `channel_id` and no context (bot-initiated).
- [ ] **AC-03**: Both tools raise `RuntimeError` when no adapter in shared state.
- [ ] **AC-04**: Agent with `discord.enabled: false` in YAML raises `PermissionError`.
- [ ] **AC-05**: All three tools registered via `@tool` and visible to `ToolCallBlock`.

## Progress

- [ ] Task started
- [ ] `send_channel_message` implemented
- [ ] `post_channel_embed` implemented
- [ ] `ask_human` implemented
- [ ] Tests pass (see T08)
- [ ] Complete
