#!/usr/bin/env python
"""Council CLI — run an agent from the command line.

Usage:
    uv run run.py --agent ceo --prompt "Develop a market entry strategy for Nigeria"
    uv run run.py --agent ceo --prompt "..." --flow inbox --session my-session-01
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).parent))

from engine.runner import AgentRunner


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="council",
        description="Run a Council agent.",
    )
    parser.add_argument("--agent", required=True, help="Agent ID (matches agents/<id>.yaml)")
    parser.add_argument("--prompt", required=True, help="Initial prompt / task description")
    parser.add_argument(
        "--flow",
        default="main",
        help="Flow name from agent YAML (default: main)",
    )
    parser.add_argument("--session", default=None, help="Session ID (auto-generated if omitted)")
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

    runner = AgentRunner(
        agent_id=args.agent,
        agents_dir=args.agents_dir,
        flows_dir=args.flows_dir,
        logs_dir=args.logs_dir,
    )
    runner.run(prompt=args.prompt, flow_name=args.flow, session_id=args.session)


if __name__ == "__main__":
    main()
