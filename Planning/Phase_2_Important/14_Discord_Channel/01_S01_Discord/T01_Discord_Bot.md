# REQ-14 Discord Channel — Implementation Plan (Local Runtime)

## Context

This is a **local-first** implementation using the existing `uv run` / APScheduler runtime.
No Lambda or webhooks. The cloud path (REQ-14 originally assumed) is deferred to Phase 3.

---

## Architecture Overview

```
Discord Server(s)
      │  on_message events
      ▼
engine/discord_gateway.py          ← discord.py persistent connection (local dev)
      │                            ← APScheduler poll mode (future / no-gateway fallback)
      │  channel_context injected into shared state
      ▼
engine/discord_router.py           ← channel_id → agent map; Nova Lite fallback
      │  👀 reaction added here
      ▼
engine/runner.py (existing)        ← agent runs normally; channel_context is opaque data
      │
      │  outbound via ChannelAdapter
      ▼
engine/channel_adapter.py          ← abstract ChannelAdapter + DiscordAdapter
      │  embed formatting, thread creation, reaction lifecycle, retry pings
      ▼
Discord Server(s)
```

**Key design rule**: all existing engine blocks (`LLMBlock`, `ToolCallBlock`, `CheckpointBlock`,
`HumanInputBlock`) stay channel-unaware. They interact with the outside world only through
`shared["channel_context"]` and the `ChannelAdapter` stored in `shared["_channel_adapter"]`.

---

## Files Created / Modified

| File | Status | Notes |
|---|---|---|
| `config/discord.yaml` | NEW | Per-instance config (see T01) |
| `agents/*.yaml` | MODIFIED | Add `discord:` block per agent (see T01) |
| `engine/channel_adapter.py` | NEW | Abstract adapter + `DiscordAdapter` (see T02) |
| `engine/discord_router.py` | NEW | Channel map + LLM fallback (see T03) |
| `engine/discord_gateway.py` | NEW | discord.py connection, event loop (see T04) |
| `tools/channel_tools.py` | NEW | `send_channel_message`, `post_channel_embed`, `ask_human` (see T05) |
| `engine/block.py` | MODIFIED | `HumanInputBlock` Discord integration + retry (see T06) |
| `run.py` | MODIFIED | `--mode discord` flag (see T07) |
| `tests/test_discord_*.py` | NEW | Unit + integration tests (see T08) |

---

## Task Execution Order

Tasks T01 and T02 can run in **parallel**.
T03 and T05 each depend only on T01/T02 — run in **parallel** after those.
T04 depends on T02 + T03. T06 depends on T04 + T05.
T07 depends on T04. T08 depends on T06 + T07.

```
T01 ──┬──> T03 ──> T04 ──> T06 ──> T08
T02 ──┘──> T05 ──>    ──> T07 ──>
```

---

## Behaviour Spec

### Threading model
- **Human-initiated** (`on_message` in a channel): router creates a Discord thread on that
  message. All bot output (responses, questions, retries, errors) goes into the thread.
  Main channel only shows the original human message + emoji reactions.
- **Bot-initiated** (proactive posts via `post_channel_embed`): direct channel post, no thread.

### Reaction lifecycle (managed by `DiscordAdapter`)
| Moment | Action |
|---|---|
| Message arrives at router | Add 👀 |
| Agent dispatched | Add agent's `emoji` from YAML |
| Agent completed successfully | Clear all reactions → add ✅ |
| Error | Clear all reactions → add ❌ → reply in thread with error text |

### Human-input retry (when agent suspends via `CheckpointBlock`)
1. Agent posts question embed in thread → suspends to disk checkpoint.
2. APScheduler retry job: ping up to **3 times**, every **4 hours during business hours**
   (09:00–18:00 in the local system timezone). Ping = reply in same thread tagging the human.
3. After 3rd unanswered ping: resume agent with system injection:
   `[SYSTEM] Human has not responded after 3 attempts. Continue without their input.`

### Clarification on routing miss
When Nova Lite router returns `unclear`, the bot posts in the originating channel:
> "I'm not sure which agent should handle that — could you be more specific,
> or mention an agent by name? Available agents: ceo, researcher…"
Reactions on the original message → ❌ (not routed).

### Agent Discord opt-out
Each agent YAML has `discord.enabled` (default `true`). Agents with `enabled: false`
are excluded from the router's candidate list and cannot use `channel_tools`.

---

## Dependencies

- `discord.py>=2.3` (pip/uv add)
- `zoneinfo` (stdlib, Python 3.9+) for business-hours tz check
- `DISCORD_BOT_TOKEN` in environment or `.env` — **only secret required, never in any config file**
- No new AWS services required

---

## Progress

- [ ] T01: Config + agent YAML extension
- [ ] T02: Channel adapter abstraction
- [ ] T03: Discord router
- [ ] T04: Discord gateway
- [ ] T05: Channel tools
- [ ] T06: HumanInputBlock extension + retry scheduler
- [ ] T07: run.py `--mode discord`
- [ ] T08: Tests
- [ ] Human walkthrough (AC-14.01 through AC-14.04)
