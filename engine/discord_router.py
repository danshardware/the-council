"""Discord message router.

Routes an inbound Discord message to an agent using:
  1. Explicit channel_id → agent mapping from config/discord.yaml
  2. Nova Lite LLM fallback (if routing_fallback_llm: true)
  3. Clarification sentinel (ROUTE_UNCLEAR) when neither works

The bot token is never touched here — it lives only in discord_gateway.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

_log = logging.getLogger(__name__)

_NOVA_LITE = "us.amazon.nova-lite-v1:0"

_ROUTING_SYSTEM = (
    "You are a routing assistant. Given a message from a Discord user, "
    "pick the single most appropriate agent to handle it.\n\n"
    "Available agents:\n{agent_list}\n\n"
    "Reply with ONLY the agent_id (e.g. \"ceo\") — a single word, nothing else. "
    "If you genuinely cannot decide, reply with the single word \"unclear\"."
)


@dataclass
class RouterResult:
    agent_id: str | None
    unclear: bool
    method: Literal["map", "llm", "unclear"]


def load_discord_config(path: str = "config/discord.yaml") -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Discord config not found: {path}\n"
            "Create config/discord.yaml — see "
            "Planning/Phase_2_Important/14_Discord_Channel for the schema."
        )
    with p.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def route_message(
    guild_id: str,
    channel_id: str,
    message_content: str,
    config: dict,
    agent_configs: dict[str, dict],
) -> RouterResult:
    """Route a Discord message to an agent.

    Args:
        guild_id: Discord guild (server) ID as a string.
        channel_id: Discord channel ID as a string.
        message_content: Raw text content of the message.
        config: Loaded discord.yaml dict.
        agent_configs: Mapping of agent_id → loaded agent YAML dict.

    Returns:
        RouterResult with agent_id (or None) and routing method.
    """
    for guild in config.get("guilds", []):
        if str(guild.get("guild_id")) != str(guild_id):
            continue
        # Guild matched — check channel map
        for ch in guild.get("channels", []):
            if str(ch.get("channel_id")) == str(channel_id):
                return RouterResult(
                    agent_id=ch["agent"],
                    unclear=False,
                    method="map",
                )
        # Guild matched but no channel entry — try LLM fallback
        if guild.get("routing_fallback_llm", False):
            return _llm_route(message_content, agent_configs)
        break  # guild found, fallback disabled

    return RouterResult(agent_id=None, unclear=True, method="unclear")


def _llm_route(message_content: str, agent_configs: dict[str, dict]) -> RouterResult:
    """Ask Nova Lite to pick the best agent. Returns UNCLEAR on any failure."""
    from conversation.conversation import Conversation, Message

    enabled = {
        aid: cfg
        for aid, cfg in agent_configs.items()
        if cfg.get("discord", {}).get("enabled", True)
    }
    if not enabled:
        return RouterResult(agent_id=None, unclear=True, method="unclear")

    agent_list = "\n".join(
        f"- {aid}: {_first_line(cfg.get('description', aid))}"
        for aid, cfg in enabled.items()
    )
    system_prompt = _ROUTING_SYSTEM.format(agent_list=agent_list)

    try:
        conv = Conversation(
            model_id=_NOVA_LITE,
            system_prompts=system_prompt,
            tools=[],
        )
        conv.conversation.append(Message("user", text=f'User message: "{message_content}"'))
        _role, text = conv.call_model()
        answer = text.strip().lower().split()[0] if text.strip() else "unclear"
    except Exception as exc:
        _log.warning("LLM routing failed: %s", exc)
        return RouterResult(agent_id=None, unclear=True, method="unclear")

    if answer == "unclear" or answer not in agent_configs:
        return RouterResult(agent_id=None, unclear=True, method="llm")

    return RouterResult(agent_id=answer, unclear=False, method="llm")


def _first_line(text: str) -> str:
    return text.strip().splitlines()[0] if text.strip() else ""
