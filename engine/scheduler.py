"""APScheduler-based scheduling engine.

Reads `config/schedules.yaml` for persistent schedule definitions and runs
agents on cron/interval/one-shot triggers.  Also drives mailbox polling so
suspended agents are resumed when inbox messages arrive.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from rich.console import Console

_console = Console()
_log = logging.getLogger(__name__)

SCHEDULES_PATH = Path("config") / "schedules.yaml"


# ---------------------------------------------------------------------------
# Schedule persistence helpers
# ---------------------------------------------------------------------------

def load_schedules(path: Path = SCHEDULES_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("schedules", [])


def save_schedules(schedules: list[dict[str, Any]], path: Path = SCHEDULES_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump({"schedules": schedules}, fh, default_flow_style=False)


def add_schedule(
    schedule_id: str,
    agent_id: str,
    prompt: str,
    trigger: str,
    trigger_args: dict[str, Any],
    flow: str = "main",
    path: Path = SCHEDULES_PATH,
) -> None:
    schedules = load_schedules(path)
    # Remove any existing entry with same ID
    schedules = [s for s in schedules if s.get("id") != schedule_id]
    schedules.append(
        {
            "id": schedule_id,
            "agent": agent_id,
            "prompt": prompt,
            "flow": flow,
            "trigger": trigger,
            "trigger_args": trigger_args,
            "enabled": True,
        }
    )
    save_schedules(schedules, path)


def remove_schedule(schedule_id: str, path: Path = SCHEDULES_PATH) -> bool:
    schedules = load_schedules(path)
    before = len(schedules)
    schedules = [s for s in schedules if s.get("id") != schedule_id]
    if len(schedules) < before:
        save_schedules(schedules, path)
        return True
    return False


# ---------------------------------------------------------------------------
# Job runner (called by APScheduler in its thread)
# ---------------------------------------------------------------------------

def _run_agent_job(agent_id: str, prompt: str, flow: str = "main") -> None:
    from engine.runner import AgentRunner
    session_id = uuid.uuid4().hex[:12]
    _console.print(
        f"[bold green][Scheduler][/bold green] Firing: agent={agent_id} "
        f"flow={flow} session={session_id}"
    )
    try:
        runner = AgentRunner(agent_id=agent_id)
        runner.run(prompt=prompt, flow_name=flow, session_id=session_id)
    except Exception as exc:
        _log.error("Scheduled job failed: agent=%s error=%s", agent_id, exc, exc_info=True)
        _console.print(f"[red][Scheduler] Job failed: {exc}[/red]")


def _poll_mailboxes() -> None:
    """Check all agent inboxes and resume suspended sessions or spawn inbox flows."""
    from engine.mailbox import Mailbox
    from engine.runner import AgentRunner
    mailbox = Mailbox()
    messages_dir = Path("messages")
    if not messages_dir.exists():
        return
    for agent_dir in messages_dir.iterdir():
        if not agent_dir.is_dir():
            continue
        agent_id = agent_dir.name
        for msg in mailbox.poll_inbox(agent_id):
            session_id = uuid.uuid4().hex[:12]
            prompt = msg.get("prompt", "")
            _console.print(
                f"[bold cyan][Mailbox][/bold cyan] Delivering to {agent_id}: "
                f"msg={msg['msg_id'][:8]}… "
            )
            try:
                runner = AgentRunner(agent_id=agent_id)
                runner.run(prompt=prompt, flow_name="inbox", session_id=session_id)
                mailbox.mark_processed(msg["_path"])
            except Exception as exc:
                _log.error(
                    "Inbox delivery failed: agent=%s msg=%s error=%s",
                    agent_id, msg["msg_id"], exc, exc_info=True,
                )
                _console.print(f"[red][Mailbox] Delivery failed: {exc}[/red]")


# ---------------------------------------------------------------------------
# Scheduler factory
# ---------------------------------------------------------------------------

def _build_trigger(trigger: str, trigger_args: dict[str, Any]):
    if trigger == "cron":
        return CronTrigger(**trigger_args)
    if trigger == "interval":
        return IntervalTrigger(**trigger_args)
    if trigger == "date":
        return DateTrigger(**trigger_args)
    raise ValueError(f"Unknown trigger type: '{trigger}'")


def build_scheduler(
    blocking: bool = True,
    mailbox_poll_seconds: int = 10,
    schedules_path: Path = SCHEDULES_PATH,
) -> BlockingScheduler | BackgroundScheduler:
    cls = BlockingScheduler if blocking else BackgroundScheduler
    scheduler = cls()

    # Mailbox poller — always added
    scheduler.add_job(
        _poll_mailboxes,
        trigger=IntervalTrigger(seconds=mailbox_poll_seconds),
        id="__mailbox_poll__",
        name="Mailbox poller",
        replace_existing=True,
    )

    # Load persistent schedules from YAML
    for sched in load_schedules(schedules_path):
        if not sched.get("enabled", True):
            continue
        try:
            trigger = _build_trigger(sched["trigger"], sched.get("trigger_args", {}))
            scheduler.add_job(
                _run_agent_job,
                trigger=trigger,
                id=sched["id"],
                name=f"agent:{sched['agent']}",
                kwargs={
                    "agent_id": sched["agent"],
                    "prompt": sched["prompt"],
                    "flow": sched.get("flow", "main"),
                },
                replace_existing=True,
            )
            _console.print(
                f"[dim]Loaded schedule: {sched['id']} → {sched['agent']} "
                f"({sched['trigger']})[/dim]"
            )
        except Exception as exc:
            _log.warning("Skipping invalid schedule %s: %s", sched.get("id"), exc)

    return scheduler
