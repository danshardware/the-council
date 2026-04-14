#!/usr/bin/env python
"""Council CLI — run an agent from the command line or start the scheduler daemon.

Usage:
    uv run run.py --agent ceo --prompt "Develop a market entry strategy for Nigeria"
    uv run run.py --agent ceo --prompt "..." --flow inbox --session my-session-01
    uv run run.py --daemon                   # start mailbox poller + scheduled jobs + any channels
    uv run run.py --daemon --local           # daemon without Discord / other channel gateways
    uv run run.py --daemon --poll-seconds 5  # faster mailbox poll interval
"""

import argparse
import os
import sys
import threading
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
        help="Start the scheduler daemon (mailbox poller + scheduled jobs + channel gateways). "
             "Mutually exclusive with --agent.",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Local-only mode: suppress all channel gateways (Discord etc.) even if credentials "
             "are available.  Useful for development and testing.",
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
        _con = Console()
        _con.print(Rule("[bold green]Council Scheduler Daemon[/bold green]"))

        if not args.local:
            _start_channel_gateways()

        scheduler = build_scheduler(blocking=True, mailbox_poll_seconds=args.poll_seconds)
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            _con.print("\n[dim]Scheduler stopped.[/dim]")
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


# ---------------------------------------------------------------------------
# Channel gateway auto-start
# ---------------------------------------------------------------------------

def _start_channel_gateways() -> None:
    """Start any available channel gateways in background daemon threads.

    A gateway starts if and only if its token env var is set AND its config
    file exists.  Missing either is silent (logged at info level only).
    """
    _start_discord_gateway()
    # Future: _start_slack_gateway(), _start_teams_gateway() …


def _start_discord_gateway(
    config_path: str = "config/discord.yaml",
) -> threading.Thread | None:
    from rich.console import Console
    _con = Console()

    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        return None

    if not Path(config_path).exists():
        _con.print(
            "[yellow][Discord] DISCORD_BOT_TOKEN found but config/discord.yaml is missing "
            "— skipping Discord gateway.[/yellow]"
        )
        return None

    try:
        from engine.discord_router import load_discord_config
        from engine.discord_gateway import build_discord_client
        config = load_discord_config(config_path)
        client = build_discord_client(config)
    except Exception as exc:
        _con.print(f"[red][Discord] Failed to initialise gateway: {exc}[/red]")
        return None

    _con.print("[bold blue][Discord][/bold blue] Starting gateway in background thread…")

    def _run() -> None:
        # discord.py's client.run() creates its own asyncio event loop
        client.run(token, log_handler=None)

    t = threading.Thread(target=_run, daemon=True, name="discord-gateway")
    t.start()
    return t


if __name__ == "__main__":
    main()
