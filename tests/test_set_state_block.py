"""Tests for SetStateBlock, _get_nested, and _set_nested."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.block import SetStateBlock, _get_nested, _set_nested


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_block(key: str, source: str | None = None, merge: bool = True, transitions: dict | None = None) -> SetStateBlock:
    config: dict = {"type": "set_state", "key": key, "merge": merge}
    if source is not None:
        config["source"] = source
    if transitions is not None:
        config["transitions"] = transitions
    return SetStateBlock(block_id="test_set", config=config)


def _shared(**kwargs) -> dict:
    base = {
        "max_iterations": 50,
        "iteration": 0,
        "messages": [],
        "block_visits": {},
        "action_input": {},
        "logger": MagicMock(),  # forbidden write target — must not be overwritten
    }
    base.update(kwargs)
    return base


def _run(block: SetStateBlock, shared: dict) -> str:
    """Drive prep → exec → post and return the transition string."""
    prep_res = block.prep(shared)
    exec_res = block.exec(prep_res)
    return block.post(shared, prep_res, exec_res)


# ---------------------------------------------------------------------------
# _get_nested
# ---------------------------------------------------------------------------

class TestGetNested:

    def test_top_level_key(self):
        assert _get_nested({"a": 1}, "a") == 1

    def test_two_levels(self):
        assert _get_nested({"a": {"b": 2}}, "a.b") == 2

    def test_three_levels(self):
        assert _get_nested({"a": {"b": {"c": 3}}}, "a.b.c") == 3

    def test_list_index(self):
        assert _get_nested({"items": ["x", "y", "z"]}, "items.1") == "y"

    def test_missing_key_raises(self):
        with pytest.raises(KeyError, match="not found"):
            _get_nested({"a": {"x": 1}}, "a.b")

    def test_bad_list_index_raises(self):
        with pytest.raises(KeyError, match="invalid"):
            _get_nested({"items": [1, 2]}, "items.99")

    def test_traversal_into_non_dict_raises(self):
        with pytest.raises(KeyError, match="Cannot traverse"):
            _get_nested({"a": "string"}, "a.b")


# ---------------------------------------------------------------------------
# _set_nested
# ---------------------------------------------------------------------------

class TestSetNested:

    def test_write_top_level(self):
        state = {}
        _set_nested(state, "task", "research", False)
        assert state["task"] == "research"

    def test_write_nested_creates_intermediates(self):
        state = {}
        _set_nested(state, "context.target", "researcher", False)
        assert state["context"]["target"] == "researcher"

    def test_dict_merge(self):
        state = {"cfg": {"a": 1}}
        _set_nested(state, "cfg", {"b": 2}, merge=True)
        assert state["cfg"] == {"a": 1, "b": 2}

    def test_dict_replace(self):
        state = {"cfg": {"a": 1}}
        _set_nested(state, "cfg", {"b": 2}, merge=False)
        assert state["cfg"] == {"b": 2}

    def test_non_dict_always_replaced(self):
        state = {"count": 1}
        _set_nested(state, "count", 2, merge=True)
        assert state["count"] == 2

    def test_forbidden_key_raises(self):
        for key in ("logger", "tool_context", "agent_config", "messages", "iteration"):
            with pytest.raises(ValueError, match="not allowed"):
                _set_nested({}, key, "x", False)

    def test_underscore_prefix_raises(self):
        with pytest.raises(ValueError, match="not allowed"):
            _set_nested({}, "_todo_list", [], False)


# ---------------------------------------------------------------------------
# SetStateBlock — transitions
# ---------------------------------------------------------------------------

class TestSetStateBlockTransitions:

    def test_set_transition_on_value(self):
        shared = _shared(action_input={"current_task": "write report"})
        block = _make_block(key="current_task")
        transition = _run(block, shared)
        assert transition == "set"
        assert shared["current_task"] == "write report"

    def test_empty_transition_on_none(self):
        shared = _shared(action_input={"current_task": None})
        block = _make_block(key="current_task")
        transition = _run(block, shared)
        assert transition == "empty"

    def test_empty_transition_on_empty_string(self):
        shared = _shared(action_input={"current_task": ""})
        block = _make_block(key="current_task")
        assert _run(block, shared) == "empty"

    def test_empty_transition_on_empty_list(self):
        shared = _shared(action_input={"current_task": []})
        block = _make_block(key="current_task")
        assert _run(block, shared) == "empty"

    def test_empty_transition_on_empty_dict(self):
        shared = _shared(action_input={"current_task": {}})
        block = _make_block(key="current_task")
        assert _run(block, shared) == "empty"

    def test_error_transition_when_wired(self):
        shared = _shared(action_input={})  # "task" missing from action_input
        block = _make_block(
            key="current_task",
            transitions={"error": "handle_err"},
        )
        transition = _run(block, shared)
        assert transition == "error"
        # State should not have been written
        assert "current_task" not in shared

    def test_error_raises_when_not_wired(self):
        shared = _shared(action_input={})
        block = _make_block(key="current_task")  # no error transition
        with pytest.raises(KeyError):
            _run(block, shared)


# ---------------------------------------------------------------------------
# SetStateBlock — source / key options
# ---------------------------------------------------------------------------

class TestSetStateBlockSourceKey:

    def test_explicit_source_path(self):
        shared = _shared(action_input={"details": {"name": "Dan"}})
        block = _make_block(key="owner", source="action_input.details.name")
        _run(block, shared)
        assert shared["owner"] == "Dan"

    def test_default_source_uses_key_leaf(self):
        # key="context.target" → default source="action_input.target"
        shared = _shared(action_input={"target": "researcher"})
        block = _make_block(key="context.target")
        _run(block, shared)
        assert shared["context"]["target"] == "researcher"

    def test_nested_write_target(self):
        shared = _shared(action_input={"agent": "ceo"})
        block = _make_block(key="delegation.target", source="action_input.agent")
        _run(block, shared)
        assert shared["delegation"]["target"] == "ceo"

    def test_merge_true_preserves_existing(self):
        shared = _shared(action_input={"extra": {"b": 2}}, meta={"a": 1})
        block = _make_block(key="meta", source="action_input.extra", merge=True)
        _run(block, shared)
        assert shared["meta"] == {"a": 1, "b": 2}

    def test_merge_false_replaces_existing(self):
        shared = _shared(action_input={"extra": {"b": 2}}, meta={"a": 1})
        block = _make_block(key="meta", source="action_input.extra", merge=False)
        _run(block, shared)
        assert shared["meta"] == {"b": 2}

    def test_write_int_value(self):
        shared = _shared(action_input={"count": 7})
        block = _make_block(key="retry_count", source="action_input.count")
        _run(block, shared)
        assert shared["retry_count"] == 7

    def test_write_list_value(self):
        shared = _shared(action_input={"items": ["a", "b", "c"]})
        block = _make_block(key="queue", source="action_input.items")
        _run(block, shared)
        assert shared["queue"] == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# SetStateBlock — forbidden write targets
# ---------------------------------------------------------------------------

class TestSetStateBlockForbiddenTargets:

    def test_cannot_write_logger(self):
        shared = _shared(action_input={"logger": "evil"})
        block = _make_block(key="logger", source="action_input.logger")
        with pytest.raises(ValueError, match="not allowed"):
            _run(block, shared)

    def test_cannot_write_underscore_key(self):
        shared = _shared(action_input={"val": []})
        block = _make_block(key="_todo_list", source="action_input.val")
        with pytest.raises(ValueError, match="not allowed"):
            _run(block, shared)
