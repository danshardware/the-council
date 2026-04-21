"""Tests for tools/outlook_tools.py — pure file I/O, no Outlook COM access."""

from __future__ import annotations

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import ToolContext


def _ctx() -> ToolContext:
    return ToolContext(agent_id="email", session_id="test-session")


# ---------------------------------------------------------------------------
# write_outlook_commands
# ---------------------------------------------------------------------------

class TestWriteOutlookCommands:
    def test_writes_yaml_file(self, tmp_path):
        commands = [
            {"action": "move", "entry_id": "AAA", "store_id": "BBB", "destination_folder": "Processed"},
            {"action": "flag", "entry_id": "CCC", "store_id": "BBB"},
            {"action": "draft", "mailbox": "user@example.com", "to": "a@b.com", "subject": "Hi", "body": "Hello"},
        ]
        with patch("tools.outlook_tools._commands_path", return_value=tmp_path / "commands.yaml"):
            from tools.outlook_tools import write_outlook_commands
            result = write_outlook_commands(commands, _ctx())

        assert "3 command(s)" in result
        written = yaml.safe_load((tmp_path / "commands.yaml").read_text(encoding="utf-8"))
        assert len(written["commands"]) == 3
        assert written["commands"][0]["action"] == "move"
        assert written["commands"][2]["subject"] == "Hi"

    def test_rejects_invalid_action(self, tmp_path):
        with patch("tools.outlook_tools._commands_path", return_value=tmp_path / "commands.yaml"):
            from tools.outlook_tools import write_outlook_commands
            result = write_outlook_commands([{"action": "delete_everything"}], _ctx())
        assert "[ERROR]" in result
        assert "delete_everything" in result

    def test_rejects_non_list(self, tmp_path):
        with patch("tools.outlook_tools._commands_path", return_value=tmp_path / "commands.yaml"):
            from tools.outlook_tools import write_outlook_commands
            result = write_outlook_commands("not a list", _ctx())
        assert "[ERROR]" in result

    def test_creates_parent_dirs(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "commands.yaml"
        with patch("tools.outlook_tools._commands_path", return_value=deep_path):
            from tools.outlook_tools import write_outlook_commands
            result = write_outlook_commands([{"action": "flag", "entry_id": "X", "store_id": "Y"}], _ctx())
        assert deep_path.exists()

    def test_empty_list_writes_empty_commands(self, tmp_path):
        with patch("tools.outlook_tools._commands_path", return_value=tmp_path / "commands.yaml"):
            from tools.outlook_tools import write_outlook_commands
            result = write_outlook_commands([], _ctx())
        assert "0 command(s)" in result
        written = yaml.safe_load((tmp_path / "commands.yaml").read_text())
        assert written["commands"] == []


# ---------------------------------------------------------------------------
# lookup_agent_directory
# ---------------------------------------------------------------------------

class TestLookupAgentDirectory:
    def _make_agents_dir(self, tmp_path: Path) -> Path:
        agents = tmp_path / "agents"
        agents.mkdir()
        (agents / "researcher.yaml").write_text(
            "id: researcher\nname: Researcher\ndescription: Does research\n",
            encoding="utf-8",
        )
        (agents / "marketing.yaml").write_text(
            "id: marketing\nname: Marketing Agent\ndescription: Handles marketing tasks\n",
            encoding="utf-8",
        )
        return agents

    def test_returns_all_agents(self, tmp_path):
        agents_dir = self._make_agents_dir(tmp_path)
        with patch("tools.outlook_tools._agents_dir", return_value=agents_dir):
            from tools.outlook_tools import lookup_agent_directory
            result = lookup_agent_directory(_ctx())
        data = yaml.safe_load(result)
        ids = [e["id"] for e in data["agent_directory"]]
        assert "researcher" in ids
        assert "marketing" in ids

    def test_includes_description(self, tmp_path):
        agents_dir = self._make_agents_dir(tmp_path)
        with patch("tools.outlook_tools._agents_dir", return_value=agents_dir):
            from tools.outlook_tools import lookup_agent_directory
            result = lookup_agent_directory(_ctx())
        data = yaml.safe_load(result)
        researcher = next(e for e in data["agent_directory"] if e["id"] == "researcher")
        assert "research" in researcher["description"].lower()

    def test_empty_agents_dir(self, tmp_path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        with patch("tools.outlook_tools._agents_dir", return_value=agents_dir):
            from tools.outlook_tools import lookup_agent_directory
            result = lookup_agent_directory(_ctx())
        assert "[]" in result

    def test_skips_malformed_yaml(self, tmp_path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "good.yaml").write_text("id: good\nname: Good\ndescription: Works\n")
        (agents_dir / "bad.yaml").write_text(": broken: [yaml\n")
        with patch("tools.outlook_tools._agents_dir", return_value=agents_dir):
            from tools.outlook_tools import lookup_agent_directory
            result = lookup_agent_directory(_ctx())
        data = yaml.safe_load(result)
        # Should contain good, not crash on bad
        assert any(e["id"] == "good" for e in data["agent_directory"])


# ---------------------------------------------------------------------------
# notify
# ---------------------------------------------------------------------------

class TestNotify:
    def test_discord_delegates_to_post_tool(self):
        with patch("tools.discord_tools.post_to_discord_channel") as mock_post:
            mock_post.return_value = "Posted 1 message(s) to channel 123"
            from tools.outlook_tools import notify
            result = notify("discord", "123", "Hello world", _ctx())
        mock_post.assert_called_once_with("123", "Hello world", _ctx())
        assert "Posted" in result

    def test_unknown_provider_returns_error(self):
        from tools.outlook_tools import notify
        result = notify("carrier_pigeon", "nest_42", "coo", _ctx())
        assert "[ERROR]" in result
        assert "carrier_pigeon" in result

    def test_discord_passes_through_error(self):
        with patch("tools.discord_tools.post_to_discord_channel") as mock_post:
            mock_post.return_value = "Error: DISCORD_BOT_TOKEN is not set."
            from tools.outlook_tools import notify
            result = notify("discord", "999", "test", _ctx())
        assert "Error" in result
