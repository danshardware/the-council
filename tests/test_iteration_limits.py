"""Tests for the iteration warning and grace-period wrap-up logic in BaseBlock."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.block import BaseBlock, MaxIterationsError


def _make_block(block_id: str = "test_block", max_visits: int | None = None) -> BaseBlock:
    config: dict = {}
    if max_visits is not None:
        config["max_visits"] = max_visits
    return BaseBlock(block_id=block_id, config=config)


def _shared(max_iterations: int = 10) -> dict:
    return {
        "max_iterations": max_iterations,
        "iteration": 0,
        "messages": [],
    }


# ---------------------------------------------------------------------------
# Normal operation
# ---------------------------------------------------------------------------

class TestNormalIteration:

    def test_increments_iteration_counter(self):
        block = _make_block()
        shared = _shared(max_iterations=5)
        block._check_iterations(shared)
        assert shared["iteration"] == 1

    def test_tracks_block_visits(self):
        block = _make_block("my_block")
        shared = _shared(max_iterations=5)
        block._check_iterations(shared)
        block._check_iterations(shared)
        assert shared["block_visits"]["my_block"] == 2

    def test_no_message_injected_well_below_limit(self):
        block = _make_block()
        shared = _shared(max_iterations=20)
        # Run 5 iterations — nowhere near warning zone
        for _ in range(5):
            block._check_iterations(shared)
        assert not any("[SYSTEM]" in m["content"] for m in shared["messages"])


# ---------------------------------------------------------------------------
# Per-block max_visits cap
# ---------------------------------------------------------------------------

class TestMaxVisits:

    def test_raises_on_max_visits_exceeded(self):
        block = _make_block(max_visits=3)
        shared = _shared(max_iterations=100)
        for _ in range(3):
            block._check_iterations(shared)
        with pytest.raises(MaxIterationsError, match="max_visits=3"):
            block._check_iterations(shared)


# ---------------------------------------------------------------------------
# Warning message
# ---------------------------------------------------------------------------

class TestWarningMessage:

    def test_warning_injected_at_warn_buffer(self):
        """Warning should appear when iteration >= max_iter - max(3, max_iter//10)."""
        block = _make_block()
        shared = _shared(max_iterations=15)  # buffer = max(3, 1) = 3 → threshold = 12
        # Drive iteration to 12 (= 15 - 3)
        for _ in range(12):
            block._check_iterations(shared)
        assert shared.get("_iteration_warned") is True
        system_msgs = [m for m in shared["messages"] if "[SYSTEM]" in m["content"]]
        assert len(system_msgs) == 1
        assert "approaching" in system_msgs[0]["content"].lower()

    def test_warning_injected_only_once(self):
        """Warning must not stack up across multiple near-limit iterations."""
        block = _make_block()
        shared = _shared(max_iterations=15)  # buffer = 3 → threshold = 12
        for _ in range(14):  # well into warning zone (but before hard stop)
            try:
                block._check_iterations(shared)
            except Exception:
                break
        system_msgs = [m for m in shared["messages"] if "approaching" in m["content"].lower()]
        assert len(system_msgs) == 1

    def test_no_warning_before_threshold(self):
        block = _make_block()
        shared = _shared(max_iterations=20)
        # Run 9 iterations (max_iter - 10 = 10, so 9 is still safe)
        for _ in range(9):
            block._check_iterations(shared)
        assert not shared.get("_iteration_warned")


# ---------------------------------------------------------------------------
# Grace period
# ---------------------------------------------------------------------------

class TestGracePeriod:

    def test_grace_mode_activated_on_first_overflow(self):
        block = _make_block()
        shared = _shared(max_iterations=3)
        for _ in range(3):
            block._check_iterations(shared)
        # Turn 4: first overflow
        block._check_iterations(shared)
        assert shared.get("_grace_mode") is True

    def test_max_iterations_bumped_by_3_on_grace(self):
        block = _make_block()
        shared = _shared(max_iterations=3)
        for _ in range(4):  # turn 4 is first overflow
            block._check_iterations(shared)
        # After grace activation, max_iterations should be current_iter + 2
        # (activation turn counts as grace turn 1 of 3)
        assert shared["max_iterations"] == shared["iteration"] + 2

    def test_grace_period_injects_final_message(self):
        block = _make_block()
        shared = _shared(max_iterations=3)
        for _ in range(4):
            block._check_iterations(shared)
        system_msgs = [m for m in shared["messages"] if "[SYSTEM]" in m["content"]]
        # At least one message should mention "iteration limit" / "3 turns"
        assert any("3 turns" in m["content"] for m in system_msgs)

    def test_grace_allows_3_more_turns(self):
        """3 total wrap-up turns (activation turn + 2 more) must not raise."""
        block = _make_block()
        shared = _shared(max_iterations=3)
        for _ in range(3):
            block._check_iterations(shared)
        # Turn 4: grace activated (wrap-up turn 1) — should not raise
        block._check_iterations(shared)
        # Turns 5, 6: wrap-up turns 2 and 3 — still no raise
        block._check_iterations(shared)
        block._check_iterations(shared)
        # No error raised — we've had exactly 3 grace turns

    def test_hard_stop_after_grace_period(self):
        """Must raise MaxIterationsError once all 3 grace turns are consumed."""
        block = _make_block()
        shared = _shared(max_iterations=3)
        # base (3) + grace activation (1) + 2 more grace turns = 6 total OK turns
        for _ in range(6):
            block._check_iterations(shared)
        with pytest.raises(MaxIterationsError):
            block._check_iterations(shared)

    def test_grace_mode_only_activates_once(self):
        """Repeated overflows must not keep bumping the limit."""
        block = _make_block()
        shared = _shared(max_iterations=3)
        # First overflow activates grace
        for _ in range(4):
            block._check_iterations(shared)
        bumped_limit = shared["max_iterations"]
        # Second overflow (still within grace) must not bump again
        block._check_iterations(shared)
        assert shared["max_iterations"] == bumped_limit
