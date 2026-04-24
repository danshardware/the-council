"""Abstract channel adapter and Discord implementation.

All agent engine blocks are channel-unaware. Any outbound communication goes
through a ChannelAdapter stored in ``shared["_channel_adapter"]``.  Future
channels (Slack, Teams) implement the same interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import discord as _discord_types


class ChannelAdapter(ABC):
    """Thin interface between the engine and an external chat channel."""

    @abstractmethod
    async def send_message(self, destination, content: str) -> None:
        """Post plain text. ``destination`` is a channel or thread object."""

    @abstractmethod
    async def send_embed(
        self,
        destination,
        title: str,
        description: str,
        agent_config: dict,
    ) -> int:
        """Post a rich embed with agent branding. Returns the new Discord message ID."""

    @abstractmethod
    async def add_reaction(self, message, emoji: str) -> None:
        """Add an emoji reaction to a message."""

    @abstractmethod
    async def clear_reactions(self, message) -> None:
        """Remove all reactions the bot has placed on a message."""

    @abstractmethod
    async def remove_own_reaction(self, message, emoji: str) -> None:
        """Remove a single reaction the bot previously placed on a message."""

    @abstractmethod
    async def create_thread(self, message, name: str):
        """Create a public thread on ``message``. Returns the thread object."""


class DiscordAdapter(ChannelAdapter):
    """Concrete ChannelAdapter backed by a ``discord.py`` Client."""

    def __init__(self, client) -> None:
        self._client = client

    async def send_message(self, destination, content: str) -> None:
        await destination.send(content)

    async def send_embed(
        self,
        destination,
        title: str,
        description: str,
        agent_config: dict,
    ) -> int:
        import discord as _discord
        d_cfg = agent_config.get("discord", {})
        color = int(d_cfg.get("embed_color", 0x5865F2))
        name = d_cfg.get("embed_name", agent_config.get("name", "Agent"))
        emoji = d_cfg.get("embed_emoji", "🤖")

        # Split into ≤4096-char chunks so long agent messages aren't silently truncated.
        _LIMIT = 4096
        chunks = []
        while len(description) > _LIMIT:
            # Try to split on a newline near the limit so we don't break mid-word.
            split_at = description.rfind("\n", 0, _LIMIT)
            if split_at == -1:
                split_at = _LIMIT
            chunks.append(description[:split_at])
            description = description[split_at:].lstrip("\n")
        chunks.append(description)

        last_id = 0
        for i, chunk in enumerate(chunks):
            chunk_title = title if i == 0 else f"{title} (cont.)"
            embed = _discord.Embed(title=chunk_title, description=chunk, color=color)
            embed.set_author(name=f"{emoji}  {name}")
            msg = await destination.send(embed=embed)
            last_id = msg.id
        return last_id

    async def add_reaction(self, message, emoji: str) -> None:
        try:
            await message.add_reaction(emoji)
        except Exception:
            pass  # reaction failures must never abort the agent flow

    async def clear_reactions(self, message) -> None:
        try:
            await message.clear_reactions()
        except Exception:
            pass

    async def remove_own_reaction(self, message, emoji: str) -> None:
        try:
            await message.remove_reaction(emoji, self._client.user)
        except Exception:
            pass

    async def create_thread(self, message, name: str):
        # Discord thread name limit is 100 characters
        name = name[:100]
        return await message.create_thread(name=name)
