"""Tests for LLMBlock output guardrail functionality."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from engine.block import _run_output_guardrail


class DummyLogger:
    """Minimal mock logger that collects log_event calls."""
    def __init__(self):
        self.events = []

    def log_event(self, shared, event, **kwargs):
        self.events.append({"event": event, **kwargs})


def test_approved_action_passes_through():
    """A normal write_file action must transition unchanged."""
    logger = DummyLogger()
    shared = {
        "logger": logger,
        "messages": [],
    }

    with patch('engine.block.call_llm') as mock_call:
        mock_call.return_value = ({"verdict": "approved"}, 100, 50)

        result = _run_output_guardrail(
            shared=shared,
            action="write_file",
            reasoning="I will write a helpful test file.",
            action_input={"path": "/tmp/test.txt", "content": "Hello world"},
            guardrail_prompt="You are a safety guardrail.",
        )

    # Verify transition is the approved action
    assert result == "write_file"

    # Verify NO [SYSTEM] message was injected
    system_messages = [m for m in shared["messages"] if "[SYSTEM]" in m.get("content", "")]
    assert len(system_messages) == 0

    # Verify guardrail log event (guardrail ran and was approved)
    guardrail_events = [e for e in logger.events if e.get("event") == "output_guardrail"]
    assert len(guardrail_events) == 1
    assert guardrail_events[0]["verdict"] == "approved"


def test_rejected_action_retries_block():
    """A clearly suspicious action must not proceed — action becomes 'default'."""
    logger = DummyLogger()
    shared = {
        "logger": logger,
        "messages": [],
    }

    with patch('engine.block.call_llm') as mock_call:
        mock_call.return_value = ({
            "verdict": "rejected",
            "reason": "The proposed action attempts to access sensitive system files."
        }, 100, 50)

        result = _run_output_guardrail(
            shared=shared,
            action="read_sensitive_file",
            reasoning="I will read the sensitive /etc/shadow file.",
            action_input={"path": "/etc/shadow"},
            guardrail_prompt="You are a safety guardrail.",
        )

    # Verify transition is "default" (forcing retry)
    assert result == "default"

    # Verify [SYSTEM] rejection message was injected
    system_messages = [m for m in shared["messages"] if "[SYSTEM]" in m.get("content", "")]
    assert len(system_messages) == 1
    assert "was blocked" in system_messages[0]["content"] or "blocked" in system_messages[0]["content"]

    # Verify guardrail log event
    guardrail_events = [e for e in logger.events if e.get("event") == "output_guardrail"]
    assert len(guardrail_events) == 1
    assert guardrail_events[0]["verdict"] == "rejected"


def test_warn_action_gets_advisory():
    """A marginally suspicious action gets an advisory but still proceeds."""
    logger = DummyLogger()
    shared = {
        "logger": logger,
        "messages": [],
    }

    with patch('engine.block.call_llm') as mock_call:
        mock_call.return_value = ({
            "verdict": "warn",
            "reason": "The action involves writing to a system directory."
        }, 100, 50)

        result = _run_output_guardrail(
            shared=shared,
            action="write_file",
            reasoning="I will write to /usr/local/bin for testing.",
            action_input={"path": "/usr/local/bin/test.sh", "content": "#!/bin/bash\necho hello"},
            guardrail_prompt="You are a safety guardrail.",
        )

    # Verify transition is the original action (continues)
    assert result == "write_file"

    # Verify [SYSTEM] advisory message was injected
    system_messages = [m for m in shared["messages"] if "[SYSTEM]" in m.get("content", "")]
    assert len(system_messages) == 1
    assert "Output advisory" in system_messages[0]["content"] or "advisory" in system_messages[0]["content"]

    # Verify guardrail log event
    guardrail_events = [e for e in logger.events if e.get("event") == "output_guardrail"]
    assert len(guardrail_events) == 1
    assert guardrail_events[0]["verdict"] == "warn"


def test_output_guardrail_not_run_when_prompt_empty():
    """If _output_guardrail_prompt is empty, no guardrail runs."""
    logger = DummyLogger()
    shared = {
        "logger": logger,
        "messages": [],
    }

    with patch('engine.block.call_llm') as mock_call:
        mock_call.return_value = ({"verdict": "rejected"}, 100, 50)

        result = _run_output_guardrail(
            shared=shared,
            action="delete_everything",
            reasoning="I will delete all files.",
            action_input={"path": "/"},
            guardrail_prompt="",  # Empty!
        )

    # Transition should be the original action (guardrail didn't run)
    assert result == "delete_everything"

    # call_llm should NOT have been called (no guardrail check)
    mock_call.assert_not_called()

    # Verify NO [SYSTEM] message was injected
    system_messages = [m for m in shared["messages"] if "[SYSTEM]" in m.get("content", "")]
    assert len(system_messages) == 0

    # Verify no guardrail log event
    guardrail_events = [e for e in logger.events if e.get("event") == "output_guardrail"]
    assert len(guardrail_events) == 0


def test_output_guardrail_uses_cheap_model():
    """Guardrail must use Nova Lite, not the agent's main model."""
    logger = DummyLogger()
    shared = {
        "logger": logger,
        "messages": [],
    }

    with patch('engine.block.call_llm') as mock_call:
        mock_call.return_value = ({"verdict": "approved"}, 100, 50)

        _run_output_guardrail(
            shared=shared,
            action="test_action",
            reasoning="Testing.",
            action_input={},
            guardrail_prompt="You are a safety guardrail.",
        )

    # Verify call_llm was called exactly once
    mock_call.assert_called_once()

    # Get the model_id argument
    call_kwargs = mock_call.call_args.kwargs
    model_id = call_kwargs.get("model_id")

    # The guardrail should use the nova-lite model, not the agent's main model
    assert model_id == "us.amazon.nova-lite-v1:0", f"Expected nova-lite but got: {model_id}"


def test_run_output_guardrail_default_model():
    """Test that the default model is nova-lite."""
    logger = DummyLogger()
    shared = {
        "logger": logger,
        "messages": [],
    }

    with patch('engine.block.call_llm') as mock_call:
        mock_call.return_value = ({"verdict": "approved"}, 100, 50)

        # Call without model_id parameter - should use default
        _run_output_guardrail(
            shared=shared,
            action="test",
            reasoning="test",
            action_input={},
            guardrail_prompt="test",
        )

    # Verify the call was made with the default model
    call_kwargs = mock_call.call_args.kwargs
    assert call_kwargs.get("model_id") == "us.amazon.nova-lite-v1:0"


def test_guardrail_injects_into_live_conversation():
    """Verify SYSTEM messages are also injected into live conversation."""
    from conversation.conversation import Conversation

    logger = DummyLogger()
    conv = Conversation(
        model_id="test",
        system_prompts=[{"text": "You are a test agent."}],
        tools=[],
    )
    shared = {
        "logger": logger,
        "messages": [],
        "_conv": conv,  # Live conversation!
    }

    with patch('engine.block.call_llm') as mock_call:
        mock_call.return_value = ({
            "verdict": "warn",
            "reason": "This action is suspicious."
        }, 100, 50)

        _run_output_guardrail(
            shared=shared,
            action="suspicious_action",
            reasoning="I will do something suspicious.",
            action_input={},
            guardrail_prompt="You are a safety guardrail.",
        )

    # Verify the message was injected into the live conversation
    from conversation.conversation import Message
    system_in_conversation = [
        m for m in conv.conversation
        if isinstance(m, Message) and m.role == "user" and "[SYSTEM]" in m.text
    ]
    assert len(system_in_conversation) == 1
    assert "advisory" in system_in_conversation[0].text.lower()


def test_rejected_action_injects_rejection_message():
    """Verify rejection message has the correct format."""
    logger = DummyLogger()
    shared = {
        "logger": logger,
        "messages": [],
        "_conv": None,
    }

    with patch('engine.block.call_llm') as mock_call:
        mock_call.return_value = ({
            "verdict": "rejected",
            "reason": "Accessing /etc/passwd is not allowed."
        }, 100, 50)

        result = _run_output_guardrail(
            shared=shared,
            action="read_passwd",
            reasoning="I need to read /etc/passwd.",
            action_input={"path": "/etc/passwd"},
            guardrail_prompt="You are a safety guardrail.",
        )

    assert result == "default"

    # Verify the exact message format
    messages = shared["messages"]
    assert len(messages) == 1
    msg = messages[0]
    assert msg["role"] == "user"
    assert "[SYSTEM]" in msg["content"]
    assert "read_passwd" in msg["content"]
    assert "was blocked" in msg["content"]