"""Outlook integration tools for the email agent.

All tools are pure file I/O — no subprocess, no COM access.
The agent runs in a Linux container; Outlook lives on the Windows host.
Files are exchanged via a shared directory (data/workspace/outlook/).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from tools import ToolContext, tool


def _commands_path() -> Path:
    from engine.paths import WORKSPACE_DIR
    return WORKSPACE_DIR / "outlook" / "commands" / "commands.yaml"


def _agents_dir() -> Path:
    from engine.paths import REPO_ROOT
    return REPO_ROOT / "agents"


# ---------------------------------------------------------------------------
# write_outlook_commands
# ---------------------------------------------------------------------------

@tool
def write_outlook_commands(commands: list, context: ToolContext) -> str:
    """Write a list of Outlook action commands to the shared commands file.

    Each command is a dict with an 'action' key and action-specific fields:
      move:   entry_id, store_id, destination_folder
      flag:   entry_id, store_id
      unflag: entry_id, store_id
      read:   entry_id, store_id
      unread: entry_id, store_id
      draft:  mailbox, to, subject, body

    The file is read by ExecuteOutlookCommands.ps1 on the Windows host.
    Overwrites any existing commands file — call once with all actions consolidated.
    """
    if not isinstance(commands, list):
        return "[ERROR] commands must be a list of dicts."

    valid_actions = {"move", "flag", "unflag", "read", "unread", "draft"}
    for cmd in commands:
        if not isinstance(cmd, dict):
            return f"[ERROR] Each command must be a dict, got: {type(cmd)}"
        action = cmd.get("action")
        if action not in valid_actions:
            return f"[ERROR] Unknown action '{action}'. Valid: {sorted(valid_actions)}"

    path = _commands_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump({"commands": commands}, fh, default_flow_style=False, allow_unicode=True)

    return f"Wrote {len(commands)} command(s) to {path}"


# ---------------------------------------------------------------------------
# lookup_agent_directory
# ---------------------------------------------------------------------------

@tool
def lookup_agent_directory(context: ToolContext) -> str:
    """Return a YAML list of all available agents with their id and description.

    Use this to decide which agent to route an email to.
    """
    agents_dir = _agents_dir()
    entries = []
    for agent_file in sorted(agents_dir.glob("*.yaml")):
        try:
            with agent_file.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if not isinstance(data, dict):
                continue
            entries.append({
                "id": data.get("id", agent_file.stem),
                "name": data.get("name", agent_file.stem),
                "description": str(data.get("description", "")).strip(),
            })
        except Exception:
            continue  # skip malformed files

    if not entries:
        return "agent_directory: []"

    return yaml.dump({"agent_directory": entries}, default_flow_style=False, allow_unicode=True)


# ---------------------------------------------------------------------------
# notify
# ---------------------------------------------------------------------------

@tool
def notify(provider: str, destination: str, content: str, context: ToolContext) -> str:
    """Send a notification message via the specified channel provider.

    Args:
        provider:    Channel type. Currently supported: "discord".
        destination: Provider-specific target (e.g. Discord channel ID).
        content:     Plain-text message to send.

    The provider and destination for each channel are configured in the agent
    YAML under 'notify_channels'. Call this once per channel entry.
    """
    if provider == "discord":
        from tools.discord_tools import post_to_discord_channel
        return post_to_discord_channel(destination, content, context)

    return f"[ERROR] Unknown provider '{provider}'. Supported: discord"
