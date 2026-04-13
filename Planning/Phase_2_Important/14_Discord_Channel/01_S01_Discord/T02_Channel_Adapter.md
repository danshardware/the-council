# T02: Channel Adapter Abstraction

## File
`engine/channel_adapter.py`

## Why
All future channels (Slack REQ-17, Teams REQ-18) share the same engine integration points.
Define the interface once here; each channel provides its own concrete `ChannelAdapter`.

## Interface

```python
from abc import ABC, abstractmethod

class ChannelAdapter(ABC):
    """Thin interface between the agent engine and an external chat channel."""

    @abstractmethod
    async def send_message(self, channel_context: dict, content: str) -> None:
        """Post plain-text content. Used for bot-initiated posts (no thread)."""

    @abstractmethod
    async def send_embed(
        self,
        channel_context: dict,
        title: str,
        description: str,
        *,
        in_thread: bool = True,
    ) -> int:
        """Post a rich embed. Returns the new message ID."""

    @abstractmethod
    async def create_thread(
        self, channel_context: dict, message_id: int, name: str
    ) -> int:
        """Create a thread on message_id. Returns thread_id."""

    @abstractmethod
    async def add_reaction(self, channel_context: dict, message_id: int, emoji: str) -> None:
        """Add a single emoji reaction to a message."""

    @abstractmethod
    async def clear_reactions(self, channel_context: dict, message_id: int) -> None:
        """Remove all reactions the bot has added to a message."""

    @abstractmethod
    async def ping_human(self, channel_context: dict, attempt: int) -> None:
        """
        Send a reminder that the agent is waiting.
        `attempt` is 1-indexed (1, 2, 3).
        """
```

## `channel_context` schema (shared across all adapters)

```python
{
    "type": "discord",          # adapter discriminator
    "guild_id": str,
    "channel_id": str,
    "message_id": int,          # original human message (for reactions)
    "thread_id": int | None,    # None until HumanInputBlock creates it
    "author_id": str,           # Discord user ID for @-mentions in pings
    "agent_emoji": str,         # pulled from agent YAML discord.emoji
    "retry_count": int,         # how many pings have been sent (0-3)
    "pending_checkpoint": str | None,  # path to checkpoint file when suspended
}
```

## `DiscordAdapter` implementation

Concrete subclass in the same file. Wraps a `discord.py` `Client` instance.
Constructor: `DiscordAdapter(client: discord.Client)`.

Key behaviours:
- `send_embed`: builds a `discord.Embed` using `channel_context["agent_emoji"]` as the
  author icon (until a real icon URL is configured), agent name from YAML as author name,
  and embed color from `discord.discord_color` in agent YAML.
- Thread creation: `channel.create_thread(name=name, message=message)` via discord.py.
- `ping_human`: `@{author_id}` mention inside the thread.
  If `thread_id` is None (shouldn't happen), falls back to the parent channel.

## Acceptance Criteria

- [ ] **AC-01**: `ChannelAdapter` is an abstract base class with all methods above.
- [ ] **AC-02**: `DiscordAdapter` implements all methods; no abstract-method errors at import.
- [ ] **AC-03**: `channel_context` schema documented and validated with a `TypedDict` or dataclass.
- [ ] **AC-04**: `DiscordAdapter` can be constructed from a `discord.Client` without errors.
- [ ] **AC-05**: No Discord imports leak outside `engine/channel_adapter.py` (lazy import guard).

## Notes

- Use `discord.py>=2.3` (async). All methods are `async`.
- Keep `SlackAdapter` / `TeamsAdapter` stubs as `NotImplementedError` raises if wanted, but
  do not implement them now (YAGNI).
- For emoji-as-icon: Discord embeds support `set_author(name=..., icon_url=...)`. Use a
  generic robot emoji 🤖 as fallback when no URL is configured.

## Progress

- [ ] Task started
- [ ] `ChannelAdapter` ABC written
- [ ] `DiscordAdapter` written
- [ ] Tests pass (see T08)
- [ ] Complete
