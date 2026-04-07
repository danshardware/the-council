"""Bedrock LLM bridge — wraps conversation.Conversation for agent block use."""

from __future__ import annotations

import re
import sys
import os
import time
from typing import Any

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from conversation.conversation import Conversation, Message, BedrockTool

_RETRY_EXCEPTIONS = (
    "ReadTimeoutError",
    "ConnectTimeoutError",
    "EndpointConnectionError",
    "ServiceUnavailableError",
    "ThrottlingException",
    "ModelTimeoutException",
)


def call_llm(
    model_id: str,
    system_prompt: str,
    messages: list[dict[str, str]],
    tools: list[BedrockTool] | None = None,
    max_retries: int = 3,
) -> tuple[dict[str, Any], int, int]:
    """
    Call Bedrock, handle any native tool-use loop, then parse the final text as YAML.
    Retries up to max_retries times on transient network/throttle errors.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return _call_once(model_id, system_prompt, messages, tools)
        except Exception as exc:
            exc_name = type(exc).__name__
            exc_str = str(exc)
            is_transient = any(r in exc_str or r in exc_name for r in _RETRY_EXCEPTIONS)
            if is_transient and attempt < max_retries - 1:
                wait = 2 ** attempt  # 1s, 2s
                print(f"[llm] Transient error ({exc_name}), retrying in {wait}s… "
                      f"(attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                last_exc = exc
            else:
                raise
    raise last_exc  # type: ignore[misc]


def _call_once(
    model_id: str,
    system_prompt: str,
    messages: list[dict[str, str]],
    tools: list[BedrockTool] | None = None,
) -> tuple[dict[str, Any], int, int]:
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
    """Extract and parse YAML from an LLM response, trying multiple strategies."""
    # Strategy 1: fenced ```yaml ... ``` block
    fenced = re.search(r"```(?:yaml)?\s*\n(.*?)```", text, re.DOTALL)
    if fenced:
        try:
            result = yaml.safe_load(fenced.group(1).strip())
            if isinstance(result, dict):
                return result
        except Exception:
            pass

    # Strategy 2: parse the whole response as YAML
    try:
        result = yaml.safe_load(text.strip())
        if isinstance(result, dict) and "action" in result:
            return result
    except Exception:
        pass

    # Strategy 3: find the first YAML-like block (lines until a blank line)
    for block in re.split(r"\n{2,}", text):
        block = block.strip()
        if block.startswith("reasoning:") or block.startswith("action:"):
            try:
                result = yaml.safe_load(block)
                if isinstance(result, dict) and "action" in result:
                    return result
            except Exception:
                pass

    # Strategy 4: pull out just the action: line
    action_match = re.search(r"^action\s*:\s*(\S+)", text, re.MULTILINE)
    if action_match:
        action = action_match.group(1).strip().rstrip("#").strip()
        reasoning_match = re.search(r"^reasoning\s*:\s*(.+)", text, re.MULTILINE)
        result: dict[str, Any] = {"action": action}
        if reasoning_match:
            result["reasoning"] = reasoning_match.group(1).strip().strip('"')
        return result

    return {"action": "default", "raw_response": text}
