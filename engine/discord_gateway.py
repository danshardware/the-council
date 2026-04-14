"""Discord gateway — connects to Discord and drives the agent reaction lifecycle.

Start via ``run.py --daemon`` when DISCORD_BOT_TOKEN and config/discord.yaml are present.
The gateway runs in a background daemon thread alongside the APScheduler daemon.

Message flow (human-initiated):
  on_message → add 👀 → route → remove 👀 → add agent emoji → create thread →
  run agent (executor) → post embed in thread → remove agent emoji → add ✅
  on ask_human/human_reply: agent posts message → suspends → waits for thread reply → resumes
  (on error: remove bot emojis → add ❌ → post error in thread)

Bot-initiated posts (alerts, briefings) go directly to the target channel — no thread.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

import yaml
from rich.console import Console

_console = Console()
_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-process registry of sessions suspended while waiting for human input.
# Maps discord thread_id (int) → pending session info dict.
# ---------------------------------------------------------------------------
_pending_sessions: dict[int, dict] = {}

# A BackgroundScheduler started lazily when the first retry is registered.
_retry_scheduler = None


def _get_retry_scheduler():
    global _retry_scheduler
    if _retry_scheduler is None:
        from apscheduler.schedulers.background import BackgroundScheduler
        _retry_scheduler = BackgroundScheduler()
        _retry_scheduler.start()
    return _retry_scheduler


def build_discord_client(config: dict, agents_dir: str = "agents"):
    """Build and return a configured discord.Client.

    The client has on_ready and on_message handlers wired up.
    Call ``client.run(token)`` to start the gateway (blocking).
    """
    try:
        import discord
    except ImportError as exc:
        raise ImportError(
            "discord.py is required for the Discord gateway. "
            "Run: uv add 'discord.py>=2.3'"
        ) from exc

    agent_configs = _load_agent_configs(agents_dir)

    intents = discord.Intents.default()
    intents.message_content = True  # privileged — must be enabled in Developer Portal
    client = discord.Client(intents=intents)

    from engine.channel_adapter import DiscordAdapter
    adapter = DiscordAdapter(client)

    @client.event
    async def on_ready() -> None:
        _console.print(
            f"[bold blue][Discord][/bold blue] Connected as "
            f"[bold]{client.user}[/bold] — listening on "
            f"{len(config.get('guilds', []))} guild(s)"
        )

    @client.event
    async def on_message(message: discord.Message) -> None:
        # Never respond to our own messages
        if message.author == client.user:
            return

        # Ignore DMs (no guild = no channel map)
        if message.guild is None:
            return

        # Thread reply — check if a suspended agent is waiting for this human
        if isinstance(message.channel, discord.Thread):
            thread_id = message.channel.id
            pending = _pending_sessions.get(thread_id)
            if pending and str(message.author.id) == pending["channel_context"]["author_id"]:
                await _resume_from_human_reply(message, pending)
            return

        await _handle_channel_message(
            message=message,
            config=config,
            agent_configs=agent_configs,
            adapter=adapter,
            loop=asyncio.get_running_loop(),
        )

    return client


async def _handle_channel_message(
    message,
    config: dict,
    agent_configs: dict[str, dict],
    adapter,
    loop: asyncio.AbstractEventLoop,
) -> None:
    from engine.discord_router import route_message

    guild_id = str(message.guild.id)
    channel_id = str(message.channel.id)

    # Signal routing in progress
    await adapter.add_reaction(message, "👀")

    result = route_message(
        guild_id=guild_id,
        channel_id=channel_id,
        message_content=message.content,
        config=config,
        agent_configs=agent_configs,
    )

    if result.unclear or result.agent_id is None:
        await adapter.remove_own_reaction(message, "👀")
        await adapter.add_reaction(message, "❌")
        available = [
            aid for aid, cfg in agent_configs.items()
            if cfg.get("discord", {}).get("enabled", True)
        ]
        await message.channel.send(
            f"I'm not sure which agent should handle that — could you be more specific? "
            f"Available agents: {', '.join(available) or '(none configured)'}"
        )
        return

    agent_id: str = result.agent_id
    agent_cfg = agent_configs.get(agent_id, {})
    agent_emoji = agent_cfg.get("discord", {}).get("emoji", "🤖")

    # Show which agent picked it up
    await adapter.add_reaction(message, agent_emoji)

    # Create thread on the original message for all bot output
    embed_name = agent_cfg.get("discord", {}).get("embed_name", agent_cfg.get("name", agent_id))
    thread_name = f"{embed_name}: {message.content[:80]}"
    try:
        thread = await adapter.create_thread(message, thread_name)
    except Exception as exc:
        _log.warning("Failed to create thread: %s", exc)
        await adapter.remove_own_reaction(message, "👀")
        await adapter.remove_own_reaction(message, agent_emoji)
        await adapter.add_reaction(message, "❌")
        await message.channel.send(f"❌ Failed to create thread: {exc}")
        return

    # Build channel_context injected into shared state
    channel_context = {
        "type": "discord",
        "guild_id": guild_id,
        "channel_id": channel_id,
        "message_id": message.id,
        "thread_id": thread.id,
        "author_id": str(message.author.id),
        "agent_emoji": agent_emoji,
        "retry_count": 0,
        "pending_checkpoint": None,
        "_timezone": config.get("timezone", "UTC"),
    }

    # Remove 👀 now that routing is done — agent emoji signals "working/waiting"
    await adapter.remove_own_reaction(message, "👀")

    # Run agent synchronously in a thread-pool executor so we don't block the
    # Discord event loop.
    session_id = uuid.uuid4().hex[:12]

    def _run() -> dict:
        from engine.runner import AgentRunner
        runner = AgentRunner(agent_id=agent_id)
        return runner.run(
            prompt=message.content,
            session_id=session_id,
            shared_overrides={
                "channel_context": channel_context,
                "_channel_adapter": adapter,
                "_discord_loop": loop,
            },
        )

    try:
        shared = await loop.run_in_executor(None, _run)
    except Exception as exc:
        _log.error("Agent run failed: agent=%s error=%s", agent_id, exc, exc_info=True)
        await adapter.remove_own_reaction(message, agent_emoji)
        await adapter.add_reaction(message, "❌")
        await thread.send(f"❌ **Error** — {type(exc).__name__}: {exc}")
        return

    response_text = _extract_final_response(shared)
    # Only post the final embed if HumanReplyBlock hasn't already delivered the
    # message to the thread (channel_context["_already_sent"] is set by that block).
    if response_text and not channel_context.get("_already_sent"):
        await adapter.send_embed(thread, "Response", response_text, agent_cfg)

    # Check for suspension (HumanInputBlock raised SuspendExecution)
    if shared.get("suspended"):
        # Register session so on_message can resume it when the human replies.
        _pending_sessions[thread.id] = {
            "channel_context": channel_context,
            "agent_id": agent_id,
            "session_id": session_id,
            "adapter": adapter,
            "loop": loop,
            "agent_cfg": agent_cfg,
            "original_message": message,
        }
        # Schedule retry pings inside business hours
        timezone = config.get("timezone", "UTC")
        _schedule_retry(
            channel_context=channel_context,
            agent_id=agent_id,
            session_id=session_id,
            adapter=adapter,
            discord_loop=loop,
            agent_cfg=agent_cfg,
            original_message=message,
            timezone=timezone,
        )
        _console.print(
            f"[yellow][Discord][/yellow] Agent {agent_id} suspended "
            f"(session {session_id}) — awaiting human reply in thread {thread.id}"
        )
        return  # leave agent emoji reaction to signal "waiting"

    await adapter.remove_own_reaction(message, agent_emoji)
    await adapter.add_reaction(message, "✅")


def _extract_final_response(shared: dict) -> str:
    """Pull the agent's final answer out of shared state.

    Returns an empty string when HumanReplyBlock already delivered the response
    directly to the Discord thread (``channel_context["_already_sent"]`` is set),
    signalling the gateway to skip the duplicate send_embed call.
    """
    # If HumanReplyBlock already posted, nothing left to do.
    if shared.get("channel_context", {}).get("_already_sent"):
        return ""

    # Best case: agent finished with action=done and wrote a summary
    if shared.get("action") == "done":
        ai = shared.get("action_input", {})
        if isinstance(ai, dict):
            summary = ai.get("summary", "")
            if summary:
                return str(summary)

    # Good case: agent used action=ask_human to deliver a message
    # (This is valid when the agent communicates a discrete response and then
    # the HumanReplyBlock delivery failed or wasn't available.)
    if shared.get("action") == "ask_human":
        ai = shared.get("action_input", {})
        if isinstance(ai, dict):
            msg = ai.get("message", "")
            if msg:
                return str(msg)

    # Fallback: last assistant message; try to parse YAML summary from it
    for msg in reversed(shared.get("messages", [])):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        try:
            import yaml as _yaml
            parsed = _yaml.safe_load(content)
            if isinstance(parsed, dict):
                ai = parsed.get("action_input", {})
                if isinstance(ai, dict):
                    if ai.get("summary"):
                        return str(ai["summary"])
                    if ai.get("message"):
                        return str(ai["message"])
        except Exception:
            pass
        return content

    return "(No response generated)"


# ---------------------------------------------------------------------------
# Retry scheduler helpers
# ---------------------------------------------------------------------------

def _schedule_retry(
    channel_context: dict,
    agent_id: str,
    session_id: str,
    adapter,
    discord_loop: asyncio.AbstractEventLoop,
    agent_cfg: dict,
    original_message,
    timezone: str = "UTC",
) -> None:
    """Register an hourly retry-ping job (business hours only)."""
    from apscheduler.triggers.cron import CronTrigger
    scheduler = _get_retry_scheduler()
    job_id = f"discord_retry_{session_id}"
    scheduler.add_job(
        _discord_retry_job,
        trigger=CronTrigger(hour="9-17", minute=0, timezone=timezone),
        kwargs={
            "channel_context": channel_context,
            "agent_id": agent_id,
            "session_id": session_id,
            "adapter": adapter,
            "discord_loop": discord_loop,
            "agent_cfg": agent_cfg,
            "original_message": original_message,
        },
        id=job_id,
        replace_existing=True,
        max_instances=1,
        name=f"Discord retry: {agent_id}/{session_id[:8]}",
    )
    _log.info("Scheduled retry job %s (tz=%s)", job_id, timezone)


def _cancel_retry(session_id: str) -> None:
    """Remove a pending retry job if it exists."""
    sched = _retry_scheduler
    if sched is None:
        return
    try:
        sched.remove_job(f"discord_retry_{session_id}")
    except Exception:
        pass


def _discord_retry_job(
    channel_context: dict,
    agent_id: str,
    session_id: str,
    adapter,
    discord_loop: asyncio.AbstractEventLoop,
    agent_cfg: dict,
    original_message,
) -> None:
    """APScheduler job: ping human (up to 3×), then resume with system injection."""
    ctx = channel_context
    ctx["retry_count"] = ctx.get("retry_count", 0) + 1
    retry_count: int = ctx["retry_count"]

    _console.print(
        f"[bold yellow][Discord Retry][/bold yellow] "
        f"agent={agent_id} session={session_id[:8]} attempt={retry_count}/3"
    )

    if retry_count <= 3:
        async def _ping() -> None:
            thread_id = ctx.get("thread_id")
            if thread_id:
                channel = adapter._client.get_channel(int(thread_id))
                if channel:
                    author_id = ctx.get("author_id", "")
                    suffix = (
                        "next two reminders" if retry_count == 1
                        else "next reminder" if retry_count == 2
                        else "final pass"
                    )
                    await channel.send(
                        f"<@{author_id}> I'm still waiting for your input "
                        f"(attempt {retry_count}/3). "
                        f"If you don't respond, I'll continue without you after the {suffix}."
                    )
        try:
            asyncio.run_coroutine_threadsafe(_ping(), discord_loop).result(timeout=10)
        except Exception as exc:
            _log.warning("Retry ping failed: %s", exc)
        return

    # --- 3 misses: cancel job, remove from registry, resume with system injection ---
    _cancel_retry(session_id)
    thread_id_int = ctx.get("thread_id")
    if thread_id_int is not None:
        _pending_sessions.pop(int(thread_id_int), None)
    ctx["pending_checkpoint"] = None
    ctx["retry_count"] = 0
    ctx["_already_sent"] = False  # reset so the resumed session can post its response

    def _run_timeout() -> dict:
        from engine.runner import AgentRunner
        runner = AgentRunner(agent_id=agent_id)
        return runner.resume(
            session_id=session_id,
            shared_overrides={
                "channel_context": ctx,
                "_channel_adapter": adapter,
                "_discord_loop": discord_loop,
            },
            extra_messages=[{
                "role": "user",
                "content": (
                    "[SYSTEM] The user has not responded after 3 attempts. "
                    "Continue and complete the task with the information you have."
                ),
            }],
        )

    try:
        shared_result = _run_timeout()
    except Exception as exc:
        _log.error("Timeout resume run failed: %s", exc, exc_info=True)
        async def _post_error() -> None:
            t_ch = adapter._client.get_channel(int(ctx.get("thread_id", 0) or 0))
            if t_ch:
                await t_ch.send(f"❌ **Error during resume** — {type(exc).__name__}: {exc}")
        try:
            asyncio.run_coroutine_threadsafe(_post_error(), discord_loop).result(timeout=10)
        except Exception:
            pass
        return

    response_text = _extract_final_response(shared_result)

    async def _post_and_react() -> None:
        if response_text and not ctx.get("_already_sent"):
            t_ch = adapter._client.get_channel(int(ctx.get("thread_id", 0) or 0))
            if t_ch:
                await adapter.send_embed(t_ch, "Response", response_text, agent_cfg)
        try:
            orig_ch = adapter._client.get_channel(int(ctx.get("channel_id", 0) or 0))
            if orig_ch:
                orig_msg = await orig_ch.fetch_message(int(ctx.get("message_id", 0) or 0))
                await adapter.remove_own_reaction(orig_msg, ctx.get("agent_emoji", ""))
                await adapter.add_reaction(orig_msg, "✅")
        except Exception as exc_r:
            _log.warning("Could not update reactions on timeout resume: %s", exc_r)

    try:
        asyncio.run_coroutine_threadsafe(_post_and_react(), discord_loop).result(timeout=15)
    except Exception as exc:
        _log.warning("Timeout resume post failed: %s", exc)


# ---------------------------------------------------------------------------
# Resume from human reply in thread
# ---------------------------------------------------------------------------

async def _resume_from_human_reply(reply, pending: dict) -> None:
    """Called by on_message when the original author replies in a suspended thread."""
    ctx: dict = pending["channel_context"]
    agent_id: str = pending["agent_id"]
    session_id: str = pending["session_id"]
    adapter = pending["adapter"]
    loop: asyncio.AbstractEventLoop = pending["loop"]
    agent_cfg: dict = pending["agent_cfg"]
    original_message = pending["original_message"]

    # Cancel retry pings and deregister session
    _cancel_retry(session_id)
    _pending_sessions.pop(reply.channel.id, None)

    if not ctx.get("pending_checkpoint"):
        return

    # Acknowledge receipt
    try:
        await reply.add_reaction("👀")
    except Exception:
        pass

    ctx["pending_checkpoint"] = None
    ctx["retry_count"] = 0
    ctx["_already_sent"] = False  # reset so the agent's next response is posted

    def _run_resume() -> dict:
        from engine.runner import AgentRunner
        runner = AgentRunner(agent_id=agent_id)
        return runner.resume(
            session_id=session_id,
            shared_overrides={
                "channel_context": ctx,
                "_channel_adapter": adapter,
                "_discord_loop": loop,
            },
            extra_messages=[
                {"role": "user", "content": f"[HUMAN] {reply.content}"},
                {
                    "role": "user",
                    "content": (
                        "[SYSTEM] The user has replied in the thread. "
                        "Continue the conversation with ask_human if needed, "
                        "or use action: done to close this session."
                    ),
                },
            ],
        )

    try:
        shared = await loop.run_in_executor(None, _run_resume)
    except Exception as exc:
        _log.error("Resume run failed: %s", exc, exc_info=True)
        await reply.channel.send(f"❌ **Error during resume** — {type(exc).__name__}: {exc}")
        return

    response_text = _extract_final_response(shared)
    if response_text and not ctx.get("_already_sent"):
        await adapter.send_embed(reply.channel, "Response", response_text, agent_cfg)

    if shared.get("suspended"):
        # Agent asked a follow-up question — re-register for another round
        _pending_sessions[reply.channel.id] = {
            "channel_context": ctx,
            "agent_id": agent_id,
            "session_id": session_id,
            "adapter": adapter,
            "loop": loop,
            "agent_cfg": agent_cfg,
            "original_message": original_message,
        }
        timezone = ctx.get("_timezone", "UTC")
        _schedule_retry(
            channel_context=ctx,
            agent_id=agent_id,
            session_id=session_id,
            adapter=adapter,
            discord_loop=loop,
            agent_cfg=agent_cfg,
            original_message=original_message,
            timezone=timezone,
        )
        return

    # Conversation complete — update original message reactions
    try:
        await adapter.remove_own_reaction(original_message, ctx.get("agent_emoji", ""))
        await adapter.add_reaction(original_message, "✅")
    except Exception:
        pass
    try:
        await reply.remove_reaction("👀", reply.guild.me)
    except Exception:
        pass


def _load_agent_configs(agents_dir: str = "agents") -> dict[str, dict]:
    configs: dict[str, dict] = {}
    for path in Path(agents_dir).glob("*.yaml"):
        try:
            with path.open(encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh)
            if cfg and cfg.get("id"):
                configs[cfg["id"]] = cfg
        except Exception as exc:
            _log.warning("Failed to load agent config %s: %s", path, exc)
    return configs
