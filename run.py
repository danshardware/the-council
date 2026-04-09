#!/usr/bin/env python
"""Council CLI — run an agent from the command line or start the scheduler daemon.

Usage:
    uv run run.py --agent ceo --prompt "Develop a market entry strategy for Nigeria"
    uv run run.py --agent ceo --prompt "..." --flow inbox --session my-session-01
    uv run run.py --daemon                   # start mailbox poller + scheduled jobs
    uv run run.py --daemon --poll-seconds 5  # faster mailbox poll interval
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from engine.runner import AgentRunner


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="council",
        description="Run a Council agent or start the scheduler daemon.",
    )
    # Daemon mode
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Start the scheduler daemon (mailbox poller + scheduled jobs). "
             "Mutually exclusive with --agent.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=10,
        help="Mailbox poll interval in seconds (daemon mode, default: 10)",
    )
    # Agent-run mode
    parser.add_argument("--agent", help="Agent ID (matches agents/<id>.yaml)")
    parser.add_argument("--prompt", help="Initial prompt / task description")
    parser.add_argument(
        "--flow",
        default="main",
        help="Flow name from agent YAML (default: main)",
    )
    parser.add_argument("--session", default=None, help="Session ID (auto-generated if omitted)")
    parser.add_argument(
        "--resume",
        metavar="SESSION_ID",
        default=None,
        help="Resume a crashed session by SESSION_ID (reads state from its log file)",
    )
    parser.add_argument(
        "--agents-dir", default="agents", help="Directory containing agent YAML files"
    )
    parser.add_argument(
        "--flows-dir", default="flows", help="Directory containing flow YAML files"
    )
    parser.add_argument(
        "--logs-dir", default="logs", help="Directory for trace logs"
    )

    args = parser.parse_args()

    if args.daemon:
        from engine.scheduler import build_scheduler
        from rich.console import Console
        from rich.rule import Rule
        Console().print(Rule("[bold green]Council Scheduler Daemon[/bold green]"))
        scheduler = build_scheduler(blocking=True, mailbox_poll_seconds=args.poll_seconds)
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            Console().print("\n[dim]Scheduler stopped.[/dim]")
        return

    if not args.agent:
        parser.error("--agent is required unless --daemon is specified")

    runner = AgentRunner(
        agent_id=args.agent,
        agents_dir=args.agents_dir,
        flows_dir=args.flows_dir,
        logs_dir=args.logs_dir,
    )

    if args.resume:
        runner.resume(session_id=args.resume)
        return

    if not args.prompt:
        parser.error("--prompt is required unless --daemon or --resume is specified")

    runner.run(prompt=args.prompt, flow_name=args.flow, session_id=args.session)


if __name__ == "__main__":
    main()
