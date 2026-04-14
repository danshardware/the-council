"""Discord tools — post messages directly to a Discord channel via REST API.

These tools require DISCORD_BOT_TOKEN to be set in the environment.
The bot must have Send Messages permission in the target channel.
Discord messages have a 2000-character limit; long content is chunked automatically.
"""

from __future__ import annotations

import os

import httpx

from tools import ToolContext, tool

_DISCORD_API = "https://discord.com/api/v10"
_MAX_CHARS = 1990  # leave 10 chars of safety margin under the 2000-char limit


def _bot_headers() -> dict[str, str]:
    token = os.environ.get("DISCORD_BOT_TOKEN", "")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN is not set.")
    return {"Authorization": f"Bot {token}", "Content-Type": "application/json"}


@tool
def post_to_discord_channel(channel_id: str, content: str, context: ToolContext) -> str:
    """Post a plain-text message to a Discord channel by ID. Long messages are split automatically.
    Requires DISCORD_BOT_TOKEN env var and the bot having Send Messages permission in the channel."""
    try:
        headers = _bot_headers()
    except ValueError as exc:
        return f"Error: {exc}"

    url = f"{_DISCORD_API}/channels/{channel_id}/messages"
    chunks = [content[i : i + _MAX_CHARS] for i in range(0, max(len(content), 1), _MAX_CHARS)]
    sent = 0
    for chunk in chunks:
        try:
            r = httpx.post(url, headers=headers, json={"content": chunk}, timeout=10)
        except httpx.RequestError as exc:
            return f"Error: network error posting to Discord — {exc}"
        if r.status_code not in (200, 201):
            return f"Error: Discord API returned {r.status_code} — {r.text[:300]}"
        sent += 1

    return f"Posted {sent} message(s) to channel {channel_id}"
