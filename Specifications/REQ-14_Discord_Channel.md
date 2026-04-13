# REQ-14: Discord Channel

## Overview
Discord bot integration enabling human-agent interaction via Discord servers.

## Source
- [00_The Council.md](../00_The%20Council.md) → Communication Channels (Discord — important)

## Phase
Phase 2 — Important

## Implementation Note

**Local-first implementation.** This spec was originally written for a Lambda/webhook architecture.
The actual implementation uses a persistent `discord.py` process started via `uv run run.py --mode discord`.
A webhook variant for cloud deployment is deferred to Phase 3.
See `Planning/Phase_2_Important/14_Discord_Channel/01_S01_Discord/T01_Discord_Bot.md` for the full plan.

## Functional Requirements

- **FR-14.01**: Discord bot connects to one or more configured guilds and channel-to-agent mappings defined in `config/discord.yaml`.
- **FR-14.02**: Human message in a mapped channel → 👀 reaction added, agent dispatched, agent emoji added.
- **FR-14.03**: Agent completes → ✅ reaction. Error → ❌ reaction + error message in thread.
- **FR-14.04**: All bot output for human-initiated conversations goes inside a Discord thread on the original message. Main channel shows only reactions.
- **FR-14.05**: Bot-initiated posts (alerts, briefings) are posted directly to the target channel — no thread.
- **FR-14.06**: Unmapped channel messages route via Nova Lite LLM fallback (if enabled) or post a clarification prompt.
- **FR-14.07**: When agent needs human input (`HumanInputBlock`): post question embed in thread, suspend to checkpoint, retry up to 3 times every 4 hours during business hours. After 3 unanswered pings, resume with `[SYSTEM]` injection.
- **FR-14.08**: Bot token stored in env var only (`DISCORD_BOT_TOKEN`); never in YAML or source.
- **FR-14.09**: Each agent has a `discord.enabled` flag (default `true`). Disabled agents are invisible to Discord routing.
- **FR-14.10**: Channel adapter is abstracted (`engine/channel_adapter.py`) so Slack/Teams can be added later without engine changes.
- **FR-14.11**: All channel interaction tools (`send_channel_message`, `post_channel_embed`, `ask_human`) are in `tools/channel_tools.py` and registered via `@tool`.

## Acceptance Criteria

- **AC-14.01**: `uv run run.py --mode discord` starts the gateway; bot appears online in Discord.
- **AC-14.02**: Human types in mapped channel → bot reacts 👀, then agent emoji, then ✅ on completion. Thread created containing agent response.
- **AC-14.03**: Human types in unmapped channel (fallback enabled) → Nova Lite routes to correct agent.
- **AC-14.04**: Human types in unmapped channel (fallback disabled) → clarification message posted in channel.
- **AC-14.05**: Agent with `discord.enabled: false` is never selected by router.
- **AC-14.06**: Agent invokes `HumanInputBlock`; question appears in thread; human doesn't reply → bot pings 3 times on business-hours schedule → agent resumes with `[SYSTEM]` message.
- **AC-14.07**: Agent invokes `post_channel_embed` proactively (no `channel_context`) → embed posted directly to specified channel, no thread.
- **AC-14.08**: Multiple guilds configured → messages from each guild routed to their own channel maps independently.

## QA Checklist

- [ ] **Unit Tests**: `tests/test_discord_router.py`, `test_discord_adapter.py`, `test_channel_tools.py`, `test_discord_retry.py`
- [ ] **Integration Tests**: `tests/test_discord_gateway.py` — mocked discord events through to runner
- [ ] **Human Walkthrough**: Live bot, mapped channel, unmapped channel, human-input question flow, proactive embed
- [ ] **Constitution: Security (VI)**: Token only in env. All inbound message content treated as untrusted.
- [ ] **Constitution: Human-in-the-Loop (VIII)**: Retry mechanism ensures humans stay in the loop; graceful fallback after 3 attempts.
- [ ] **Constitution: YAGNI (VII)**: Lambda/webhook variant not built until Phase 3 cloud work begins.

## Dependencies

- **Depends on**: REQ-05 (Workflow engine, CheckpointBlock), REQ-08 (tool registration patterns)
- **Blocks**: REQ-17, REQ-18 (Slack and Teams reuse `engine/channel_adapter.py` abstraction)
