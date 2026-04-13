# T04: Discord Gateway

## File
`engine/discord_gateway.py`

## Purpose
Connects to Discord, receives messages, drives the reaction lifecycle, creates threads,
dispatches to the agent runner, and posts responses. Supports two run modes:

| Mode | How | When |
|---|---|---|
| **gateway** (default) | `discord.py` persistent WebSocket connection | Local dev / always-on process |
| **poll** | HTTP REST via `aiohttp`, called on APScheduler interval | Fallback; cloud where persistent process is impractical |

---

## `on_message` event flow (gateway mode)

```
on_message(message)
  │
  ├─ Ignore:  bot's own messages, messages inside threads (handled via thread watcher)
  │
  ├─ add_reaction(message, "👀")                          ← routing in progress
  │
  ├─ result = router.route_message(guild_id, channel_id, content, ...)
  │
  ├─ if result.unclear:
  │     clear_reactions(message)
  │     add_reaction(message, "❌")
  │     post clarification text in channel (not a thread)
  │     return
  │
  ├─ add_reaction(message, agent_emoji)                   ← agent identified
  │
  ├─ thread = await channel.create_thread(
  │       name=f"{agent_embed_name}: {message.content[:50]}",
  │       message=message,
  │   )
  │
  ├─ channel_context = build_channel_context(message, thread, agent_config)
  │
  ├─ Run agent in executor thread (non-blocking):
  │     runner.run(prompt=message.content, ..., shared_overrides={"channel_context": ...})
  │
  ├─ On success:
  │     clear_reactions(message)
  │     add_reaction(message, "✅")
  │
  └─ On error:
        clear_reactions(message)
        add_reaction(message, "❌")
        await thread.send(f"❌ Error: {exc}")
```

## Agent runner integration

`AgentRunner.run()` is synchronous and blocking. It must be called in a thread pool
executor so it does not block the asyncio event loop:

```python
loop = asyncio.get_event_loop()
await loop.run_in_executor(None, _run_agent_sync, agent_id, prompt, channel_context, adapter)
```

`_run_agent_sync` creates an `AgentRunner`, injects `channel_context` and `_channel_adapter`
into a `shared_overrides` dict, and calls `runner.run()`. The runner passes `shared_overrides`
into the initial `shared` state before the flow starts.

`AgentRunner.run()` needs a small extension: accept `shared_overrides: dict | None = None`
and merge it into `shared` before the flow runs. (One-line change in `runner.py`.)

## Thread watcher — reply detection

When an agent suspends (checkpoint), it writes `channel_context["pending_checkpoint"]`
with the checkpoint file path, and `channel_context["thread_id"]` with the Discord thread ID.

The gateway registers a separate `on_message` listener that:
- Checks if the message was sent inside a tracked thread (maintained in an in-memory dict
  `_pending_threads: dict[int, dict]` mapping `thread_id → channel_context`).
- If yes: load checkpoint, inject the human's reply as the resumption prompt, run agent.

`_pending_threads` is populated by `HumanInputBlock` via a callback registered on the adapter.
It is in-process memory (lost on restart), so checkpoints survive but in-thread reply detection
does not survive a gateway restart. Acceptable for local dev; cloud version uses persistent state.

## Proactive / bot-initiated posts

Agents can call `tools/channel_tools.py:post_channel_embed(...)` without a `channel_context`
(i.e., no originating human message). In this case:
- The embed is posted directly to the target `channel_id` (no thread, no reactions).
- The agent must supply `channel_id` explicitly in the tool call.

## Acceptance Criteria

- [ ] **AC-01**: Gateway starts, connects to Discord, logs "Connected as <bot name>".
- [ ] **AC-02**: Human message in a mapped channel → 👀 + agent emoji reactions appear.
- [ ] **AC-03**: Agent completes → ✅ reaction; error → ❌ + error text in thread.
- [ ] **AC-04**: Thread is created on the original message; all bot output goes in thread.
- [ ] **AC-05**: Human message in unmapped channel (fallback disabled) → clarification posted in channel.
- [ ] **AC-06**: Bot's own messages do not trigger `on_message` routing.
- [ ] **AC-07**: `AgentRunner.run()` is not blocking the asyncio event loop.
- [ ] **AC-08**: Bot token read from `os.environ["DISCORD_BOT_TOKEN"]`; never from config file or source code. Startup prints `[Discord] Token loaded from DISCORD_BOT_TOKEN` (not the value).

## Dependencies

- `discord.py>=2.3`
- T02 (`DiscordAdapter`)
- T03 (`discord_router`)
- Minor extension to `engine/runner.py`: `shared_overrides` parameter

## Progress

- [ ] Task started
- [ ] `on_message` handler implemented
- [ ] Thread creation and reaction lifecycle
- [ ] Executor-based async→sync runner bridge
- [ ] Thread watcher + `_pending_threads` tracking
- [ ] `runner.py` `shared_overrides` extension
- [ ] Tests pass (see T08)
- [ ] Complete
