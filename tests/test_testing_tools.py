"""Tests for testing_tools: list_agent_sessions, read_session_log,
agent_test, and agent_test_modify.

All filesystem access is redirected to tmp_path via monkeypatching
engine.paths so real data is never touched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import ToolContext
from tools.testing_tools import (
    agent_test,
    agent_test_modify,
    list_agent_sessions,
    read_session_log,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def ctx() -> ToolContext:
    return ToolContext(
        agent_id="agent_creator",
        session_id="testctx",
        allowed_paths=[],
        allowed_commands=[],
    )


@pytest.fixture()
def patch_paths(tmp_path: Path, monkeypatch):
    """Redirect engine.paths LOGS_DIR and WORKSPACE_DIR to tmp_path."""
    import engine.paths as ep
    import tools.testing_tools as tt

    monkeypatch.setattr(ep, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(ep, "WORKSPACE_DIR", tmp_path / "workspace")
    # The module captures paths at import time via `from engine import paths`,
    # so we also patch the module-level reference inside testing_tools.
    monkeypatch.setattr(tt, "_LOGS_DIR", lambda: tmp_path / "logs")
    monkeypatch.setattr(tt, "_WORKSPACE_DIR", lambda: tmp_path / "workspace")
    return tmp_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_log(logs_dir: Path, agent_id: str, session_id: str, events: list[dict]) -> Path:
    log_dir = logs_dir / agent_id
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{session_id}.jsonl"
    with log_path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev) + "\n")
    return log_path


def _write_checkpoint(workspace_dir: Path, agent_id: str, session_id: str, ts: str, data: dict) -> Path:
    cp_dir = workspace_dir / agent_id / session_id / "_checkpoints"
    cp_dir.mkdir(parents=True, exist_ok=True)
    cp_path = cp_dir / f"checkpoint_{ts}.json"
    cp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return cp_path


def _sample_events(session_id: str = "sess1") -> list[dict]:
    return [
        {"ts": "2026-04-22T10:00:00Z", "agent_id": "myagent", "session_id": session_id,
         "event": "session_start", "prompt": "hello world"},
        {"ts": "2026-04-22T10:00:05Z", "agent_id": "myagent", "session_id": session_id,
         "event": "block_enter", "block": "think", "iteration": 1},
        {"ts": "2026-04-22T10:00:10Z", "agent_id": "myagent", "session_id": session_id,
         "event": "llm_call", "block": "think", "action": "search"},
        {"ts": "2026-04-22T10:00:12Z", "agent_id": "myagent", "session_id": session_id,
         "event": "block_enter", "block": "apply", "iteration": 2},
        {"ts": "2026-04-22T10:00:20Z", "agent_id": "myagent", "session_id": session_id,
         "event": "llm_call", "block": "apply", "action": "done"},
        {"ts": "2026-04-22T10:00:25Z", "agent_id": "myagent", "session_id": session_id,
         "event": "session_end", "total_iterations": 2},
    ]


# ---------------------------------------------------------------------------
# list_agent_sessions
# ---------------------------------------------------------------------------

class TestListAgentSessions:
    def test_no_sessions_returns_message(self, patch_paths, ctx):
        result = list_agent_sessions("myagent", context=ctx)
        assert "No sessions" in result

    def test_lists_existing_sessions(self, patch_paths, ctx):
        logs_dir = patch_paths / "logs"
        _write_log(logs_dir, "myagent", "sess_abc", _sample_events("sess_abc"))
        _write_log(logs_dir, "myagent", "sess_xyz", _sample_events("sess_xyz"))

        result = list_agent_sessions("myagent", context=ctx)
        assert "sess_abc" in result
        assert "sess_xyz" in result

    def test_includes_checkpoint_info(self, patch_paths, ctx):
        logs_dir = patch_paths / "logs"
        ws_dir = patch_paths / "workspace"
        _write_log(logs_dir, "myagent", "sess1", _sample_events())
        _write_checkpoint(ws_dir, "myagent", "sess1", "20260422T100010Z", {"x": 1})

        result = list_agent_sessions("myagent", context=ctx)
        assert "checkpoint_20260422T100010Z" in result
        assert "checkpoint_count: 1" in result


# ---------------------------------------------------------------------------
# read_session_log
# ---------------------------------------------------------------------------

class TestReadSessionLog:
    def test_missing_log(self, patch_paths, ctx):
        result = read_session_log("myagent", "nonexistent", context=ctx)
        assert "No log" in result

    def test_formats_block_and_event(self, patch_paths, ctx):
        logs_dir = patch_paths / "logs"
        _write_log(logs_dir, "myagent", "sess1", _sample_events())

        result = read_session_log("myagent", "sess1", context=ctx)
        assert "[think]" in result
        assert "llm_call" in result
        assert "session_start" in result

    def test_shows_block_dash_for_session_events(self, patch_paths, ctx):
        logs_dir = patch_paths / "logs"
        events = [
            {"ts": "2026-04-22T10:00:00Z", "agent_id": "a", "session_id": "s",
             "event": "session_start", "prompt": "hi"},
        ]
        _write_log(logs_dir, "a", "s", events)
        result = read_session_log("a", "s", context=ctx)
        # session_start has no block field — should show "—"
        assert "[—]" in result

    def test_handles_malformed_line(self, patch_paths, ctx):
        logs_dir = patch_paths / "logs"
        log_dir = logs_dir / "myagent"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "sess1.jsonl").write_text('{"valid": true}\nNOT JSON\n', encoding="utf-8")

        result = read_session_log("myagent", "sess1", context=ctx)
        assert "MALFORMED" in result


# ---------------------------------------------------------------------------
# agent_test_modify — remove_last_turn
# ---------------------------------------------------------------------------

class TestAgentTestModifyRemoveLastTurn:
    def test_removes_last_jsonl_line(self, patch_paths, ctx):
        logs_dir = patch_paths / "logs"
        events = _sample_events()
        _write_log(logs_dir, "myagent", "sess1", events)

        result = agent_test_modify("myagent", "sess1", action="remove_last_turn", context=ctx)

        lines = (logs_dir / "myagent" / "sess1.jsonl").read_text().splitlines()
        assert len(lines) == len(events) - 1
        # The removed line was the session_end event
        assert "session_end" in result

    def test_empty_log_graceful(self, patch_paths, ctx):
        logs_dir = patch_paths / "logs"
        log_dir = logs_dir / "myagent"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "sess1.jsonl").write_text("", encoding="utf-8")

        result = agent_test_modify("myagent", "sess1", action="remove_last_turn", context=ctx)
        assert "empty" in result.lower()

    def test_missing_log(self, patch_paths, ctx):
        result = agent_test_modify("myagent", "no_sess", action="remove_last_turn", context=ctx)
        assert "No log" in result


# ---------------------------------------------------------------------------
# agent_test_modify — remove_last_run
# ---------------------------------------------------------------------------

class TestAgentTestModifyRemoveLastRun:
    def test_removes_newest_checkpoint(self, patch_paths, ctx):
        ws_dir = patch_paths / "workspace"
        cp1 = _write_checkpoint(ws_dir, "myagent", "sess1", "20260422T100000Z", {"turn": 1})
        cp2 = _write_checkpoint(ws_dir, "myagent", "sess1", "20260422T100010Z", {"turn": 2})

        result = agent_test_modify("myagent", "sess1", action="remove_last_run", context=ctx)

        assert not cp2.exists()
        assert cp1.exists()
        assert "checkpoint_20260422T100010Z" in result

    def test_no_checkpoints_returns_message(self, patch_paths, ctx):
        result = agent_test_modify("myagent", "sess1", action="remove_last_run", context=ctx)
        assert "No checkpoints" in result

    def test_trims_log_entries_after_prev_checkpoint(self, patch_paths, ctx):
        ws_dir = patch_paths / "workspace"
        logs_dir = patch_paths / "logs"

        # Checkpoint timestamps
        _write_checkpoint(ws_dir, "myagent", "sess1", "20260422T100005Z", {})  # prev
        _write_checkpoint(ws_dir, "myagent", "sess1", "20260422T100015Z", {})  # newest (to remove)

        # Log events: two before and one after the prev checkpoint ts
        events = [
            {"ts": "2026-04-22T10:00:00Z", "agent_id": "a", "session_id": "sess1", "event": "block_enter", "block": "think"},
            {"ts": "2026-04-22T10:00:05Z", "agent_id": "a", "session_id": "sess1", "event": "llm_call", "block": "think"},
            {"ts": "2026-04-22T10:00:20Z", "agent_id": "a", "session_id": "sess1", "event": "llm_call", "block": "apply"},
        ]
        _write_log(logs_dir, "myagent", "sess1", events)

        agent_test_modify("myagent", "sess1", action="remove_last_run", context=ctx)

        remaining = (logs_dir / "myagent" / "sess1.jsonl").read_text().splitlines()
        # Only the two events at/before 10:00:05Z should remain
        assert len(remaining) == 2
        assert all(json.loads(l)["ts"] <= "2026-04-22T10:00:05Z" for l in remaining)


# ---------------------------------------------------------------------------
# agent_test_modify — modify_checkpoint
# ---------------------------------------------------------------------------

class TestAgentTestModifyModifyCheckpoint:
    def test_merges_patch_into_checkpoint(self, patch_paths, ctx):
        ws_dir = patch_paths / "workspace"
        cp = _write_checkpoint(ws_dir, "myagent", "sess1", "20260422T100000Z",
                               {"action": "think", "iteration": 3})

        agent_test_modify(
            "myagent", "sess1",
            action="modify_checkpoint",
            patch_json='{"action": "apply"}',
            context=ctx,
        )

        data = json.loads(cp.read_text())
        assert data["action"] == "apply"
        assert data["iteration"] == 3  # untouched key preserved

    def test_targets_newest_checkpoint(self, patch_paths, ctx):
        ws_dir = patch_paths / "workspace"
        _write_checkpoint(ws_dir, "myagent", "sess1", "20260422T100000Z", {"v": 1})
        cp2 = _write_checkpoint(ws_dir, "myagent", "sess1", "20260422T100010Z", {"v": 2})

        agent_test_modify(
            "myagent", "sess1",
            action="modify_checkpoint",
            patch_json='{"v": 99}',
            context=ctx,
        )

        assert json.loads(cp2.read_text())["v"] == 99

    def test_invalid_patch_json_returns_error(self, patch_paths, ctx):
        ws_dir = patch_paths / "workspace"
        _write_checkpoint(ws_dir, "myagent", "sess1", "20260422T100000Z", {})

        result = agent_test_modify(
            "myagent", "sess1",
            action="modify_checkpoint",
            patch_json="NOT JSON",
            context=ctx,
        )
        assert "Invalid" in result

    def test_no_checkpoints_returns_message(self, patch_paths, ctx):
        result = agent_test_modify("myagent", "sess1", action="modify_checkpoint", context=ctx)
        assert "No checkpoints" in result


# ---------------------------------------------------------------------------
# agent_test — restart
# ---------------------------------------------------------------------------

class TestAgentTestRestart:
    def test_deletes_log_and_workspace(self, patch_paths, ctx):
        logs_dir = patch_paths / "logs"
        ws_dir = patch_paths / "workspace"

        log_path = _write_log(logs_dir, "myagent", "sess1", _sample_events())
        cp = _write_checkpoint(ws_dir, "myagent", "sess1", "20260422T100010Z", {})

        fake_shared = {"session_id": "sess1", "iteration": 1, "messages": [
            {"role": "assistant", "content": "done"}
        ]}
        with patch("engine.runner.AgentRunner") as MockRunner:
            MockRunner.return_value.run.return_value = fake_shared
            agent_test("myagent", "sess1", block_name="", action="restart", context=ctx)

        assert not log_path.exists()
        assert not cp.exists()

    def test_passes_original_prompt_to_runner(self, patch_paths, ctx):
        logs_dir = patch_paths / "logs"
        events = [
            {"ts": "2026-04-22T10:00:00Z", "agent_id": "myagent", "session_id": "sess1",
             "event": "session_start", "prompt": "Build me an agent"},
        ]
        _write_log(logs_dir, "myagent", "sess1", events)

        fake_shared = {"session_id": "sess1", "iteration": 0, "messages": []}
        with patch("engine.runner.AgentRunner") as MockRunner:
            MockRunner.return_value.run.return_value = fake_shared
            agent_test("myagent", "sess1", block_name="", action="restart", context=ctx)
            call_kwargs = MockRunner.return_value.run.call_args
            assert call_kwargs.kwargs.get("prompt") == "Build me an agent"


# ---------------------------------------------------------------------------
# agent_test — resume
# ---------------------------------------------------------------------------

class TestAgentTestResume:
    def test_trims_log_after_named_block(self, patch_paths, ctx):
        logs_dir = patch_paths / "logs"
        ws_dir = patch_paths / "workspace"
        events = _sample_events()
        _write_log(logs_dir, "myagent", "sess1", events)
        _write_checkpoint(ws_dir, "myagent", "sess1", "20260422T100005Z", {"_conv_turns": []})

        fake_shared = {"session_id": "sess1", "iteration": 1, "messages": []}
        with patch("engine.runner.AgentRunner") as MockRunner:
            MockRunner.return_value.run.return_value = fake_shared
            agent_test("myagent", "sess1", block_name="think", action="resume", context=ctx)

        remaining = (logs_dir / "myagent" / "sess1.jsonl").read_text().splitlines()
        # Events at/before the last "think" event (index 2, ts 10:00:10Z) should remain
        assert all(
            json.loads(l).get("ts", "z") <= "2026-04-22T10:00:10Z"
            for l in remaining if l.strip()
        )

    def test_deletes_checkpoints_newer_than_block_ts(self, patch_paths, ctx):
        logs_dir = patch_paths / "logs"
        ws_dir = patch_paths / "workspace"
        events = _sample_events()
        _write_log(logs_dir, "myagent", "sess1", events)

        # Two checkpoints: one before and one after the last "think" event (10:00:10Z)
        cp_keep = _write_checkpoint(ws_dir, "myagent", "sess1", "20260422T100008Z", {"_conv_turns": []})
        cp_remove = _write_checkpoint(ws_dir, "myagent", "sess1", "20260422T100020Z", {})

        fake_shared = {"session_id": "sess1", "iteration": 1, "messages": []}
        with patch("engine.runner.AgentRunner") as MockRunner:
            MockRunner.return_value.run.return_value = fake_shared
            agent_test("myagent", "sess1", block_name="think", action="resume", context=ctx)

        assert cp_keep.exists()
        assert not cp_remove.exists()

    def test_block_not_found_returns_error(self, patch_paths, ctx):
        logs_dir = patch_paths / "logs"
        _write_log(logs_dir, "myagent", "sess1", _sample_events())

        result = agent_test("myagent", "sess1", block_name="nonexistent_block",
                            action="resume", context=ctx)
        assert "not found" in result.lower()

    def test_resume_calls_runner_with_resume_from_block(self, patch_paths, ctx):
        logs_dir = patch_paths / "logs"
        ws_dir = patch_paths / "workspace"
        _write_log(logs_dir, "myagent", "sess1", _sample_events())
        _write_checkpoint(ws_dir, "myagent", "sess1", "20260422T100005Z",
                          {"_conv_turns": [{"role": "user", "content": "hi"}]})

        fake_shared = {"session_id": "sess1", "iteration": 1, "messages": []}
        with patch("engine.runner.AgentRunner") as MockRunner:
            MockRunner.return_value.run.return_value = fake_shared
            agent_test("myagent", "sess1", block_name="think", action="resume", context=ctx)

            call_kwargs = MockRunner.return_value.run.call_args
            assert call_kwargs.kwargs.get("resume_from_block") == "think"
