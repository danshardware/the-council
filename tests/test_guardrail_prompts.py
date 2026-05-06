"""Tests for the input_safety and output_safety guardrail prompts.

Structural tests (config validity) always run.
LLM verdict tests make live Bedrock calls via Nova Lite and are integration tests.

Run all:
    uv run pytest tests/test_guardrail_prompts.py -v

Run only structural (fast):
    uv run pytest tests/test_guardrail_prompts.py -v -k "Config"

Run only LLM verdict tests (slow, requires Bedrock):
    uv run pytest tests/test_guardrail_prompts.py -v -k "Verdict"
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.llm import call_llm

_GUARDRAILS_PATH = Path(__file__).parent.parent / "config" / "guardrails.yaml"
_DATA_PATH = Path(__file__).parent / "data"
_NOVA_LITE = "us.amazon.nova-lite-v1:0"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_guardrails() -> dict:
    with _GUARDRAILS_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _load_yaml(file_path: Path) -> list[dict]:
    """Load a YAML file and return its contents."""
    with file_path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _run_guardrail(system_prompt: str, user_content: str) -> tuple[str, str]:
    """Call Nova Lite with a guardrail prompt and return (verdict, reason)."""
    parsed, _, _ = call_llm(
        model_id=_NOVA_LITE,
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    return parsed.get("verdict", ""), parsed.get("reason", "")


def _format_output_safety_input(action: str, reasoning: str, action_input: dict) -> str:
    """Format output safety test case into readable text representation."""
    input_str = f"Action: {action}\nReasoning: {reasoning}\n"
    if action_input:
        input_str += f"Input: {action_input}"
    return input_str


# ---------------------------------------------------------------------------
# Load test cases from external YAML files
# ---------------------------------------------------------------------------

# Load basic test cases from YAML files
_REJECTED_INPUTS = _load_yaml(_DATA_PATH / "rejected_inputs.yaml")
_APPROVED_INPUTS = _load_yaml(_DATA_PATH / "approved_inputs.yaml")
_REJECTED_OUTPUTS = _load_yaml(_DATA_PATH / "rejected_outputs.yaml")
_APPROVED_OUTPUTS = _load_yaml(_DATA_PATH / "approved_outputs.yaml")
_CONVERSATION_TESTS = _load_yaml(_DATA_PATH / "conversation_tests.yaml")

# ---------------------------------------------------------------------------
# Structural: config file loads and has required keys
# ---------------------------------------------------------------------------

class TestGuardrailConfig:
    def test_guardrails_yaml_exists(self):
        assert _GUARDRAILS_PATH.exists(), f"guardrails.yaml not found at {_GUARDRAILS_PATH}"

    def test_guardrails_yaml_is_valid_yaml(self):
        data = _load_guardrails()
        assert isinstance(data, dict)

    def test_input_safety_key_present(self):
        data = _load_guardrails()
        assert "input_safety" in data, (
            "Missing 'input_safety' key in guardrails.yaml"
        )

    def test_output_safety_key_present(self):
        data = _load_guardrails()
        assert "output_safety" in data, (
            "Missing 'output_safety' key in guardrails.yaml"
        )

    def test_input_safety_is_nonempty_string(self):
        data = _load_guardrails()
        prompt = data["input_safety"]
        assert isinstance(prompt, str) and len(prompt) > 50

    def test_output_safety_is_nonempty_string(self):
        data = _load_guardrails()
        prompt = data["output_safety"]
        assert isinstance(prompt, str) and len(prompt) > 50

    def test_input_safety_contains_verdict_instructions(self):
        data = _load_guardrails()
        prompt = data["input_safety"]
        assert "approved" in prompt
        assert "rejected" in prompt
        assert "verdict" in prompt

    def test_output_safety_contains_verdict_instructions(self):
        data = _load_guardrails()
        prompt = data["output_safety"]
        assert "approved" in prompt
        assert "rejected" in prompt
        assert "verdict" in prompt

    def test_input_safety_under_400_tokens(self):
        """Keep prompts under 400 tokens - they run on every message, cost matters."""
        data = _load_guardrails()
        prompt = data["input_safety"]
        # Rough token estimate: ~4 chars per token
        assert len(prompt) < 1600, f"input_safety prompt too long: {len(prompt)} chars"

    def test_output_safety_under_400_tokens(self):
        """Keep prompts under 400 tokens - they run on every message, cost matters."""
        data = _load_guardrails()
        prompt = data["output_safety"]
        # Rough token estimate: ~4 chars per token
        assert len(prompt) < 1600, f"output_safety prompt too long: {len(prompt)} chars"


# ---------------------------------------------------------------------------
# LLM verdict tests: input_safety
# ---------------------------------------------------------------------------

class TestInputSafetyVerdicts:
    """Live Bedrock calls — require AWS credentials and Nova Lite access."""

    @pytest.fixture(autouse=True)
    def prompt(self):
        self._prompt = _load_guardrails()["input_safety"]

    def _check(self, message: str) -> tuple[str, str]:
        return _run_guardrail(self._prompt, f"Incoming user message:\n{message}")

    @pytest.mark.parametrize("test_case", _REJECTED_INPUTS, ids=lambda c: c.get("description", ""))
    def test_rejected_inputs(self, test_case):
        """Test cases that must be REJECTED by input_safety."""
        verdict, _ = self._check(test_case["input"])
        assert verdict == "rejected", f"Expected rejected for '{test_case['description']}', got {verdict!r}"

    @pytest.mark.parametrize("test_case", _APPROVED_INPUTS, ids=lambda c: c.get("description", ""))
    def test_approved_inputs(self, test_case):
        """Test cases that must be APPROVED by input_safety."""
        verdict, _ = self._check(test_case["input"])
        assert verdict == "approved", f"Expected approved for '{test_case['description']}', got {verdict!r}"


# ---------------------------------------------------------------------------
# LLM verdict tests: output_safety
# ---------------------------------------------------------------------------

class TestOutputSafetyVerdicts:
    """Live Bedrock calls — require AWS credentials and Nova Lite access."""

    @pytest.fixture(autouse=True)
    def prompt(self):
        self._prompt = _load_guardrails()["output_safety"]

    def _check(self, action: str, reasoning: str, action_input: dict) -> tuple[str, str]:
        content = f"Proposed action: {action}\nReasoning: {reasoning}\nAction input: {action_input}"
        return _run_guardrail(self._prompt, content)

    @pytest.mark.parametrize("test_case", _REJECTED_OUTPUTS, ids=lambda c: c.get("description", ""))
    def test_rejected_outputs(self, test_case):
        """Test cases that must be REJECTED by output_safety."""
        verdict, _ = self._check(
            test_case["action"],
            test_case["reasoning"],
            test_case.get("action_input", {}),
        )
        assert verdict == "rejected", f"Expected rejected for '{test_case['description']}', got {verdict!r}"

    @pytest.mark.parametrize("test_case", _APPROVED_OUTPUTS, ids=lambda c: c.get("description", ""))
    def test_approved_outputs(self, test_case):
        """Test cases that must be APPROVED by output_safety."""
        verdict, _ = self._check(
            test_case["action"],
            test_case["reasoning"],
            test_case.get("action_input", {}),
        )
        assert verdict == "approved", f"Expected approved for '{test_case['description']}', got {verdict!r}"


# ---------------------------------------------------------------------------
# LLM verdict tests: conversation-style input_safety
# ---------------------------------------------------------------------------

class TestConversationSafetyVerdicts:
    """Conversation-style tests that embed rejected prompts in realistic contexts.

    These tests verify that the input_safety guardrail works correctly when
    rejected prompts are embedded within normal conversation context.
    This represents more realistic usage patterns.
    """

    @pytest.fixture(autouse=True)
    def prompt(self):
        self._prompt = _load_guardrails()["input_safety"]

    def _check(self, message: str) -> tuple[str, str]:
        return _run_guardrail(self._prompt, f"Incoming user message:\n{message}")

    @pytest.mark.parametrize("test_case", _CONVERSATION_TESTS, ids=lambda c: c.get("description", ""))
    def test_conversation_inputs(self, test_case):
        """Test conversation-style inputs and verify expected verdict."""
        verdict, _ = self._check(test_case["final_input"])
        expected = test_case["expected_verdict"]
        assert verdict == expected, (
            f"Expected {expected} for '{test_case['description']}', got {verdict!r}. "
            f"Notes: {test_case.get('notes', 'N/A')}"
        )