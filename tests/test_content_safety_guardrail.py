"""
Tests for the content_safety guardrail with company_info.yaml template integration.

These tests verify:
1. Structural integrity of config/company_info.yaml
2. Template rendering works correctly for content_safety guardrail
3. LLM verdicts are correct with default company_info (needs_confirmation to prompt onboarding)
4. LLM verdicts are correct with configured company_info (proper content review)

Run all tests:
    uv run pytest tests/test_content_safety_guardrail.py -v

Run only structural (fast):
    uv run pytest tests/test_content_safety_guardrail.py -v -k "Config"

Run only LLM verdict tests (slow, requires Bedrock):
    uv run pytest tests/test_content_safety_guardrail.py -v -k "Verdict"
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.llm import call_llm
from engine.template import _load_config_dir, render_prompt

# Paths
_COMPANY_INFO_PATH = Path(__file__).parent.parent / "config" / "company_info.yaml"
_GUARDRAILS_PATH = Path(__file__).parent.parent / "config" / "guardrails.yaml"
_DATA_CONFIG_PATH = Path("data/config/company_info.yaml")
_NOVA_LITE = "us.amazon.nova-lite-v1:0"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_aws_credentials():
    """Check if AWS credentials are configured (basic check)."""
    import os
    return (
        os.environ.get("AWS_ACCESS_KEY_ID") and
        os.environ.get("AWS_SECRET_ACCESS_KEY") or
        Path.home().joinpath(".aws/credentials").exists()
    )


def _require_aws():
    """Decorator-like check that skips the test if AWS is not configured."""
    if not _check_aws_credentials():
        pytest.skip(
            "AWS credentials not configured - set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
        )


def _ensure_no_override():
    """Ensure no override company_info.yaml exists in data/config/."""
    if _DATA_CONFIG_PATH.exists():
        _DATA_CONFIG_PATH.unlink()
    # Clear the cache to force reload
    _load_config_dir.cache_clear()


def _write_override_company_info(name: str, description: str, restricted_topics: list[str]):
    """Write an override company_info.yaml to data/config/."""
    _DATA_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    override_data = {
        "name": name,
        "description": description,
        "restricted_topics": restricted_topics,
    }
    with _DATA_CONFIG_PATH.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(override_data, fh)
    # Clear the cache to force reload
    _load_config_dir.cache_clear()


def _cleanup_override():
    """Clean up override and clear cache."""
    if _DATA_CONFIG_PATH.exists():
        _DATA_CONFIG_PATH.unlink()
    _load_config_dir.cache_clear()


# ---------------------------------------------------------------------------
# Structural tests: company_info.yaml validation
# ---------------------------------------------------------------------------

class TestCompanyInfoConfig:
    """Structural tests for config/company_info.yaml file."""

    def test_company_info_yaml_exists(self):
        """Verify the built-in company_info.yaml exists."""
        assert _COMPANY_INFO_PATH.exists(), (
            f"company_info.yaml not found at {_COMPANY_INFO_PATH}"
        )

    def test_company_info_yaml_is_valid_yaml(self):
        """Verify company_info.yaml is valid YAML."""
        with _COMPANY_INFO_PATH.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        assert isinstance(data, dict), "company_info.yaml should be a YAML dict"

    def test_company_info_has_required_keys(self):
        """Verify company_info.yaml has name, description, and restricted_topics."""
        with _COMPANY_INFO_PATH.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        assert "name" in data, "company_info.yaml must have 'name' key"
        assert "description" in data, "company_info.yaml must have 'description' key"
        assert "restricted_topics" in data, (
            "company_info.yaml must have 'restricted_topics' key"
        )

    def test_company_info_default_is_unconfigured_instance(self):
        """Verify the default company_info indicates unconfigured state."""
        with _COMPANY_INFO_PATH.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        assert "unconfigured" in data["name"].lower(), (
            "Default name should indicate unconfigured state"
        )
        assert "onboarding" in data["description"].lower(), (
            "Default description should mention onboarding"
        )

    def test_company_info_restricted_topics_is_list(self):
        """Verify restricted_topics is a list."""
        with _COMPANY_INFO_PATH.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        assert isinstance(data.get("restricted_topics", []), list), (
            "restricted_topics should be a list"
        )


# ---------------------------------------------------------------------------
# Template rendering tests
# ---------------------------------------------------------------------------

class TestContentSafetyTemplateRendering:
    """Tests for template rendering of content_safety guardrail."""

    def setup_method(self):
        """Clean up any override before each test."""
        _ensure_no_override()

    def teardown_method(self):
        """Clean up override after each test."""
        _cleanup_override()

    def test_content_safety_uses_company_info_template_vars(self):
        """Verify content_safety in guardrails.yaml references company_info template vars."""
        with _GUARDRAILS_PATH.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        prompt = data["content_safety"]
        assert "{{config.company_info.name}}" in prompt, (
            "content_safety should reference {{config.company_info.name}}"
        )
        assert "{{config.company_info.description}}" in prompt, (
            "content_safety should reference {{config.company_info.description}}"
        )
        assert "{{#config.company_info.restricted_topics}}" in prompt, (
            "content_safety should use Mustache section for restricted_topics"
        )

    def test_default_company_info_renders_correctly(self):
        """Test that the default company_info renders properly in content_safety."""
        cfg = _load_config_dir()
        prompt = cfg["guardrails"]["content_safety"]
        rendered = render_prompt(prompt, {})
        # Should contain the unconfigured instance text
        assert "unconfigured Council instance" in rendered, (
            "Default company_info.name should render to 'unconfigured Council instance'"
        )

    def test_override_company_info_renders_correctly(self):
        """Test that override company_info takes priority."""
        _write_override_company_info(
            name="Test Corp",
            description="A test company for unit testing",
            restricted_topics=["test restriction"],
        )
        cfg = _load_config_dir()
        prompt = cfg["guardrails"]["content_safety"]
        rendered = render_prompt(prompt, {})
        # Should contain the override values
        assert "Test Corp" in rendered, "Override name should render"
        assert "test company for unit testing" in rendered, (
            "Override description should render"
        )
        assert "test restriction" in rendered, "Override restricted_topics should render"


# ---------------------------------------------------------------------------
# LLM verdict tests: content_safety guardrail
# ---------------------------------------------------------------------------

class TestContentSafetyVerdicts:
    """Live Bedrock calls — require AWS credentials and Nova Lite access."""

    def setup_method(self):
        """Clean up any override before each test."""
        _ensure_no_override()

    def teardown_method(self):
        """Clean up override after each test."""
        _cleanup_override()

    def _get_rendered_prompt(self) -> str:
        """Get the rendered content_safety prompt."""
        cfg = _load_config_dir()
        prompt = cfg["guardrails"]["content_safety"]
        return render_prompt(prompt, {})

    def _check(self, user_content: str) -> tuple[str, str]:
        """Call Nova Lite with content_safety prompt and return (verdict, reason)."""
        rendered = self._get_rendered_prompt()
        parsed, _, _ = call_llm(
            model_id=_NOVA_LITE,
            system_prompt=rendered,
            messages=[{"role": "user", "content": user_content}],
        )
        return parsed.get("verdict", ""), parsed.get("reason", "")

    def test_without_company_info_returns_needs_confirmation(self):
        """
        Without data/config/company_info.yaml, content_safety must return
        needs_confirmation with a message to run onboarding.

        This is a structural test that verifies the default behavior.
        """
        # Ensure cache is cleared and no override exists
        _ensure_no_override()

        verdict, reason = self._check("Post this: Our product is the best!")
        assert verdict == "needs_confirmation", (
            f"Expected needs_confirmation for benign content with default company_info, got {verdict!r}"
        )
        assert "onboarding" in reason.lower(), (
            f"Reason should mention 'onboarding', got: {reason}"
        )

    def test_with_configured_company_info_approves_benign_content(self):
        """
        With data/config/company_info.yaml present, content_safety should
        approve normal benign content.
        """
        _write_override_company_info(
            name="Acme Corp",
            description="B2B SaaS for HR teams",
            restricted_topics=["competitor disparagement"],
        )

        verdict, reason = self._check("Here's our quarterly update on project progress.")
        assert verdict == "approved", (
            f"Expected approved for benign content, got {verdict!r}: {reason}"
        )

    def test_with_configured_company_info_rejects_restricted_topics(self):
        """
        With configured restricted_topics, content_safety should reject
        content that touches those topics.
        """
        _write_override_company_info(
            name="Acme Corp",
            description="B2B SaaS for HR teams",
            restricted_topics=["competitor disparagement"],
        )

        verdict, reason = self._check("Competitor XYZ's product is terrible and broken.")
        assert verdict in ("rejected", "needs_confirmation"), (
            f"Expected rejection for competitor disparagement, got {verdict!r}: {reason}"
        )

    def test_rendered_default_prompt_mentions_onboarding(self):
        """
        Verify that the rendered default prompt explicitly tells the LLM
        to ask users to run onboarding.
        """
        rendered = self._get_rendered_prompt()
        assert "onboarding" in rendered.lower(), (
            f"Default prompt should mention onboarding, rendered: {rendered[:200]}..."
        )
        assert "needs_confirmation" in rendered, (
            "Default prompt should instruct to return needs_confirmation"
        )