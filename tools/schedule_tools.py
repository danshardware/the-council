"""Tools for agents to manage scheduled tasks."""

from __future__ import annotations

import uuid

from tools import ToolContext, tool


@tool
def schedule_agent(
    agent_id: str,
    prompt: str,
    trigger: str,
    trigger_args: str,
    flow: str,
    schedule_id: str,
    context: ToolContext,
) -> str:
    """
    Schedule an agent to run on a trigger.

    Args:
        agent_id:     Target agent (e.g. 'researcher').
        prompt:       Prompt to pass when the schedule fires.
        trigger:      One of 'cron', 'interval', 'date'.
        trigger_args: YAML-formatted trigger arguments, e.g. 'hours: 1' or
                      'hour: 9\\nminute: 30' for cron.
        flow:         Flow name to run (default 'main' if blank).
        schedule_id:  Unique ID for this schedule (auto-generated if blank).
    """
    import yaml
    from engine.scheduler import add_schedule

    sid = schedule_id.strip() if schedule_id.strip() else uuid.uuid4().hex[:8]
    flow = flow.strip() or "main"
    try:
        args: dict = yaml.safe_load(trigger_args) or {}
    except Exception as exc:
        return f"error: invalid trigger_args YAML — {exc}"

    add_schedule(
        schedule_id=sid,
        agent_id=agent_id,
        prompt=prompt,
        trigger=trigger,
        trigger_args=args,
        flow=flow,
    )
    return f"Schedule created: id={sid} agent={agent_id} trigger={trigger}"


@tool
def cancel_schedule(schedule_id: str, context: ToolContext) -> str:
    """Cancel (remove) a scheduled task by its ID."""
    from engine.scheduler import remove_schedule
    removed = remove_schedule(schedule_id)
    if removed:
        return f"Schedule '{schedule_id}' cancelled."
    return f"No schedule found with id='{schedule_id}'."


@tool
def list_schedules(context: ToolContext) -> str:
    """List all defined schedules from config/schedules.yaml."""
    import yaml
    from engine.scheduler import load_schedules
    schedules = load_schedules()
    if not schedules:
        return "schedules: none defined"
    return yaml.dump({"schedules": schedules}, default_flow_style=False)
