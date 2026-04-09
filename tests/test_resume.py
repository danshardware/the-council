"""Tests for session workspace checkpoints and workspace file summary."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# save_session_checkpoint / latest_session_checkpoint
# ---------------------------------------------------------------------------

class TestSessionCheckpoint:

    def test_creates_file_in_checkpoints_subdir(self, tmp_path):
        from engine.state import save_session_checkpoint
        shared = {"messages": [{"role": "user", "content": "hello"}], "iteration": 1}
        cp = save_session_checkpoint(shared, tmp_path)
        assert cp.parent.name == "_checkpoints"
        assert cp.exists()

    def test_filename_is_chronological(self, tmp_path):
        from engine.state import save_session_checkpoint
        shared = {"messages": [], "iteration": 1}
        cp = save_session_checkpoint(shared, tmp_path)
        # Name must match checkpoint_YYYYMMDDTHHMMSSZ.json
        import re
        assert re.match(r"checkpoint_\d{8}T\d{6}Z\.json", cp.name), cp.name

    def test_checkpoint_contains_messages(self, tmp_path):
        from engine.state import save_session_checkpoint
        msgs = [{"role": "user", "content": "test"}]
        shared = {"messages": msgs, "iteration": 5}
        cp = save_session_checkpoint(shared, tmp_path)
        data = json.loads(cp.read_text(encoding="utf-8"))
        assert data["messages"] == msgs
        assert data["iteration"] == 5

    def test_skips_logger_and_tool_context(self, tmp_path):
        from engine.state import save_session_checkpoint

        class FakeLogger:
            pass

        shared = {"messages": [], "logger": FakeLogger(), "tool_context": object()}
        cp = save_session_checkpoint(shared, tmp_path)
        data = json.loads(cp.read_text(encoding="utf-8"))
        assert "logger" not in data
        assert "tool_context" not in data

    def test_multiple_checkpoints_accumulate(self, tmp_path):
        from engine.state import save_session_checkpoint
        shared = {"messages": [], "iteration": 1}
        save_session_checkpoint(shared, tmp_path)
        time.sleep(1.1)  # ensure different second → different filename
        save_session_checkpoint(shared, tmp_path)
        cp_dir = tmp_path / "_checkpoints"
        files = list(cp_dir.glob("checkpoint_*.json"))
        assert len(files) == 2


class TestLatestSessionCheckpoint:

    def test_returns_none_when_no_checkpoints_dir(self, tmp_path):
        from engine.state import latest_session_checkpoint
        assert latest_session_checkpoint(tmp_path) is None

    def test_returns_none_when_dir_empty(self, tmp_path):
        from engine.state import latest_session_checkpoint
        (tmp_path / "_checkpoints").mkdir()
        assert latest_session_checkpoint(tmp_path) is None

    def test_returns_single_checkpoint(self, tmp_path):
        from engine.state import save_session_checkpoint, latest_session_checkpoint
        shared = {"messages": [{"role": "user", "content": "hi"}]}
        save_session_checkpoint(shared, tmp_path)
        cp = latest_session_checkpoint(tmp_path)
        assert cp is not None
        assert cp.name.startswith("checkpoint_")

    def test_returns_latest_of_multiple(self, tmp_path):
        """Latest by lexicographic sort of timestamp names."""
        from engine.state import latest_session_checkpoint
        cp_dir = tmp_path / "_checkpoints"
        cp_dir.mkdir()
        # Write three files with deliberate order
        for name in ["checkpoint_20260101T120000Z.json",
                     "checkpoint_20260101T130000Z.json",
                     "checkpoint_20260101T110000Z.json"]:
            (cp_dir / name).write_text("{}", encoding="utf-8")
        latest = latest_session_checkpoint(tmp_path)
        assert latest.name == "checkpoint_20260101T130000Z.json"


# ---------------------------------------------------------------------------
# workspace_file_summary
# ---------------------------------------------------------------------------

class TestWorkspaceFileSummary:

    def test_empty_workspace_returns_empty_string(self, tmp_path):
        from engine.state import workspace_file_summary
        assert workspace_file_summary(tmp_path) == ""

    def test_nonexistent_workspace_returns_empty_string(self, tmp_path):
        from engine.state import workspace_file_summary
        assert workspace_file_summary(tmp_path / "does_not_exist") == ""

    def test_lists_file_with_content(self, tmp_path):
        from engine.state import workspace_file_summary
        (tmp_path / "report.md").write_text("# My Report\nSome content.", encoding="utf-8")
        summary = workspace_file_summary(tmp_path)
        assert "report.md" in summary
        assert "# My Report" in summary

    def test_large_file_is_truncated(self, tmp_path):
        from engine.state import workspace_file_summary, _WORKSPACE_CONTENT_LIMIT
        big_content = "x" * (_WORKSPACE_CONTENT_LIMIT + 100)
        (tmp_path / "big.md").write_text(big_content, encoding="utf-8")
        summary = workspace_file_summary(tmp_path)
        assert "truncated" in summary
        assert big_content not in summary  # full text not present

    def test_skips_checkpoints_subdir(self, tmp_path):
        from engine.state import workspace_file_summary
        (tmp_path / "_checkpoints").mkdir()
        (tmp_path / "_checkpoints" / "checkpoint_20260101T120000Z.json").write_text(
            '{"messages": []}', encoding="utf-8"
        )
        (tmp_path / "plan.md").write_text("# Plan", encoding="utf-8")
        summary = workspace_file_summary(tmp_path)
        assert "_checkpoints" not in summary
        assert "plan.md" in summary

    def test_includes_multiple_files(self, tmp_path):
        from engine.state import workspace_file_summary
        (tmp_path / "plan.md").write_text("Plan content", encoding="utf-8")
        (tmp_path / "report.md").write_text("Report content", encoding="utf-8")
        summary = workspace_file_summary(tmp_path)
        assert "plan.md" in summary
        assert "report.md" in summary
        assert "Plan content" in summary
        assert "Report content" in summary
