"""Bedrock LLM bridge — wraps conversation.Conversation for agent block use."""

from __future__ import annotations

import re
import sys
import os
from typing import Any

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from conversation.conversation import Conversation, Message, BedrockTool


def call_llm(
    model_id: str,
    system_prompt: str,
    messages: list[dict[str, str]],
    tools: list[BedrockTool] | None = None,
) -> tuple[dict[str, Any], int, int]:
    """
    Call Bedrock, handle any native tool-use loop, then parse the final text as YAML.

    Args:
        model_id:      Bedrock model ID.
        system_prompt: Block-level system prompt.
        messages:      Prior conversation as [{"role": ..., "content": ...}, ...].
        tools:         Optional BedrockTool instances for native tool calling.

    Returns:
        (parsed_dict, input_tokens, output_tokens)
        parsed_dict always has at least {"action": str}; may contain "action_input", etc.
    """
    conv = Conversation(
        model_id=model_id,
        system_prompts=system_prompt,
        tools=tools or [],
    )

    for msg in messages:
        content = msg["content"]
        if isinstance(content, str):
            conv.conversation.append(Message(msg["role"], text=content))
        else:
            conv.conversation.append(Message(msg["role"], content=content))

    _role, text = conv.call_model()
    parsed = _parse_yaml_response(text)
    return parsed, conv.input_tokens, conv.output_tokens


def _parse_yaml_response(text: str) -> dict[str, Any]:
    """Extract and parse YAML from an LLM response, handling optional fenced blocks."""
    # Strip fenced code block wrapper if present
    fenced = re.search(r"```(?:yaml)?\s*\n(.*?)```", text, re.DOTALL)
    yaml_text = fenced.group(1).strip() if fenced else text.strip()

    try:
        result = yaml.safe_load(yaml_text)
        if isinstance(result, dict):
            return result
    except Exception:
        pass

    # Last-resort: try to pull out just the action line
    action_match = re.search(r"^action\s*:\s*(\S+)", yaml_text, re.MULTILINE)
    if action_match:
        return {"action": action_match.group(1), "raw_response": text}

    return {"action": "default", "raw_response": text}
