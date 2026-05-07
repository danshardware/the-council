"""Tests for the concierge onboarding flow.

Run all tests:
    uv run pytest tests/test_onboarding_flow.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.runner import AgentRunner

# Path for temporary workspace
_TESTS_DATA_PATH = Path(__file__).parent / "data"


class TestOnboardDone:
    """Test that the onboard_done block delivers messages to the user."""

    def setup_method(self):
        """Ensure a clean workspace directory for each test."""
        workspace_path = _TESTS_DATA_PATH / "workspace" / "concierge"
        workspace_path.mkdir(parents=True, exist_ok=True)
        return None

    def test_onboard_done_delivers_message(self):
        """
        Run the onboarding flow when mission.md already exists.
        The flow should route to already_done and deliver a message.
        """
        # Pre-create mission.md so onboarding routes to already_done path
        mission_path = Path("data/shared_knowledge/company/mission.md")
        mission_path.parent.mkdir(parents=True, exist_ok=True)
        mission_path.write_text("# Mission\nTest mission content\n", encoding="utf-8")

        # Run concierge with flow=onboarding
        runner = AgentRunner(agent_id="concierge")
        shared = runner.run(prompt="Begin onboarding.", flow_name="onboarding")

        # Assertions
        messages = [m for m in shared.get("messages", []) if m["role"] == "assistant"]
        assert len(messages) > 0, "Expected at least one assistant message in shared[messages]"

        # Check that messages contain the onboarding completion language
        content_lower = " ".join(m["content"].lower() for m in messages)
        assert "set up" in content_lower or "onboarding" in content_lower, (
            f"Expected messages to contain 'set up' or 'onboarding'. Got: {messages}"
        )

        # Verify the flow terminated (iteration should be non-zero)
        assert shared.get("iteration", 0) > 0, "Flow should have executed at least one iteration"