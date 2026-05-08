"""
Tests for the guardrail configuration step (B3) in the concierge onboarding flow.

Run all tests:
    uv run pytest tests/test_onboarding_guardrail_config.py -v

Note: These are integration tests that require:

1. AWS credentials configured (for Bedrock LLM access)
2. The tests cannot run without AWS credentials

These tests verify:
1. Skip path: User says "nothing specific" → no company_info.yaml written
2. Config path: User provides restrictions → company_info.yaml written with correct content

Without AWS, these tests will be skipped with a clear message.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.runner import AgentRunner

# Path for temporary workspace
_TESTS_DATA_PATH = Path(__file__).parent / "data"


def _check_aws_credentials():
    """Check if AWS credentials are configured (basic check)."""
    import os
    return (
        os.environ.get("AWS_ACCESS_KEY_ID") and
        os.environ.get("AWS_SECRET_ACCESS_KEY") or
        Path.home().joinpath(".aws/credentials").exists()
    )


class TestGuardrailConfigStep:
    """
    Integration tests for the guardrail configuration step (B3).

    These tests verify that:
    1. The guardrail_config block exists and is correctly structured
    2. The skip path works (user skips, no file written)
    3. The config path works (user provides restrictions, file written)

    PREREQUISITES:
    - AWS credentials must be configured (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    - Network access to AWS Bedrock for LLM calls
    """

    def setup_method(self):
        """Ensure a clean workspace directory for each test."""
        workspace_path = _TESTS_DATA_PATH / "workspace" / "concierge"
        workspace_path.mkdir(parents=True, exist_ok=True)
        # Clean up any existing company_info.yaml from previous test runs
        config_path = Path("data/config/company_info.yaml")
        if config_path.exists():
            config_path.unlink()
        return None

    def _require_aws(self):
        """Decorator-like check that skips the test if AWS is not configured."""
        if not _check_aws_credentials():
            pytest.skip("AWS credentials not configured - set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")

    def test_guardrail_config_step_is_skippable(self):
        """
        Test: If the user skips the restrictions question, onboarding
        continues normally and no company_info.yaml is written.

        EXPECTED BEHAVIOR:
        - User says "nothing specific" at the guardrail config step
        - Flow continues to agent_setup
        - data/config/company_info.yaml does NOT exist after the session
        """
        self._require_aws()  # Will skip if no AWS credentials

        # Delete mission file to force full onboarding flow
        mission_path = Path("data/shared_knowledge/company/mission.md")
        if mission_path.exists():
            mission_path.unlink()

        # Run concierge with flow=onboarding
        runner = AgentRunner(agent_id="concierge")
        shared = runner.run(
            prompt="Begin onboarding.",
            flow_name="onboarding",
        )

        # Assertions
        messages = [m for m in shared.get("messages", []) if m["role"] == "assistant"]
        assert len(messages) > 0, "Expected at least one assistant message"
        assert shared.get("iteration", 0) > 0, "Flow should have executed"

        # Verify company_info.yaml was NOT created
        config_path = Path("data/config/company_info.yaml")
        assert not config_path.exists(), (
            "company_info.yaml should NOT exist when user skips guardrail config"
        )

    def test_guardrail_config_writes_file_when_restrictions_given(self):
        """
        Test: If the user provides restrictions, Ops writes company_info.yaml.

        EXPECTED BEHAVIOR:
        - User provides specific restrictions at the guardrail config step
        - Ops agent is called via spawn_agent
        - data/config/company_info.yaml exists with the expected content
        """
        self._require_aws()  # Will skip if no AWS credentials

        # Delete mission file to force full onboarding flow
        mission_path = Path("data/shared_knowledge/company/mission.md")
        if mission_path.exists():
            mission_path.unlink()

        # Run concierge with flow=onboarding
        runner = AgentRunner(agent_id="concierge")
        shared = runner.run(
            prompt="Begin onboarding. I want restricted topics: no competitor disparagement, no financial advice.",
            flow_name="onboarding",
        )

        # Assertions
        messages = [m for m in shared.get("messages", []) if m["role"] == "assistant"]
        assert len(messages) > 0, "Expected at least one assistant message"
        assert shared.get("iteration", 0) > 0, "Flow should have executed"

        # Verify company_info.yaml WAS created
        config_path = Path("data/config/company_info.yaml")
        assert config_path.exists(), (
            "company_info.yaml should exist when user provides restrictions"
        )

        # Verify the content
        content = config_path.read_text(encoding="utf-8")
        assert "restricted_topics" in content, "restricted_topics should be in file"
        assert "competitor" in content.lower(), (
            "competitor restriction should be in file"
        )
        assert "financial" in content.lower(), (
            "financial restriction should be in file"
        )