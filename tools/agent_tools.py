"""Agent communication tools."""

from __future__ import annotations

from tools import ToolContext, tool


@tool
def spawn_agent(target_agent: str, prompt: str, context: ToolContext) -> str:
    """Spawn a sub-agent synchronously and return its result. Blocks until complete."""
    from engine.runner import AgentRunner
    runner = AgentRunner(agent_id=target_agent)
    shared = runner.run(prompt=prompt)
    messages = shared.get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            return str(msg.get("content", ""))
    return f"[Agent '{target_agent}' completed with no assistant output]"


@tool
def send_message(target_agent: str, prompt: str, context: ToolContext) -> str:
    """Send an async message to another agent's mailbox. Returns immediately."""
    from engine.mailbox import Mailbox
    mailbox = Mailbox()
    msg_id = mailbox.send(
        target_agent=target_agent,
        prompt=prompt,
        from_agent=context.agent_id,
        from_session=context.session_id,
    )
    return f"Message queued for '{target_agent}' (id={msg_id})"
