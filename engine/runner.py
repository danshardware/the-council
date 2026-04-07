"""AgentRunner — loads an agent definition + flow and drives execution."""

from __future__ import annotations

import uuid
from pathlib import Path

import yaml
from rich.console import Console
from rich.rule import Rule

from engine.block import MaxIterationsError, SuspendExecution
from engine.flow_loader import load_flow
from engine.logger import Logger
from tools import ToolContext

_console = Console()


class AgentRunner:
    def __init__(
        self,
        agent_id: str,
        agents_dir: str = "agents",
        flows_dir: str = "flows",
        logs_dir: str = "logs",
    ) -> None:
        self.agent_id = agent_id
        self.agents_dir = Path(agents_dir)
        self.flows_dir = Path(flows_dir)
        self.logs_dir = Path(logs_dir)

    def run(
        self,
        prompt: str,
        flow_name: str = "main",
        session_id: str | None = None,
    ) -> dict:
        """
        Run the agent with the given prompt.

        Args:
            prompt:     Initial user message.
            flow_name:  Key from agent YAML `flows:` section (default "main").
            session_id: Optional; auto-generated if not provided.

        Returns:
            The final shared state dict.
        """
        session_id = session_id or uuid.uuid4().hex[:12]

        # Load agent definition
        agent_config = self._load_agent()

        # Resolve flow file name
        flow_file_key = agent_config["flows"].get(flow_name)
        if flow_file_key is None:
            raise ValueError(
                f"Agent '{self.agent_id}' has no flow named '{flow_name}'"
            )
        flow_path = self.flows_dir / f"{flow_file_key}.yaml"

        # Load flow
        flow, flow_config = load_flow(flow_path)

        # Iteration cap: lower of agent vs flow
        agent_max = agent_config.get("max_iterations", 50)
        flow_max = flow_config.get("max_iterations", 25)
        max_iterations = min(agent_max, flow_max)

        # Build shared state
        shared: dict = {
            "agent_id": self.agent_id,
            "session_id": session_id,
            "logs_dir": str(self.logs_dir),
            "agent_config": agent_config,
            "max_iterations": max_iterations,
            "iteration": 0,
            "block_visits": {},
            "action": None,
            "action_input": {},
            "messages": [{"role": "user", "content": prompt}],
            "initial_prompt": prompt,
            "logger": Logger(str(self.logs_dir), self.agent_id, session_id),
            "tool_context": ToolContext(
                agent_id=self.agent_id,
                session_id=session_id,
                allowed_paths=agent_config.get("permissions", {}).get(
                    "workspace_paths", []
                ),
                allowed_commands=agent_config.get("permissions", {}).get(
                    "allowed_commands", []
                ),
            ),
        }

        _console.print(Rule(f"[bold green]Council — {self.agent_id} — {session_id}[/bold green]"))
        _console.print(f"[dim]Flow: {flow_file_key}  |  Max iterations: {max_iterations}[/dim]\n")

        with shared["logger"]:
            shared["logger"].log_event(
                shared,
                "session_start",
                flow=flow_file_key,
                prompt=prompt,
            )
            try:
                flow._run(shared)
            except MaxIterationsError as exc:
                shared["logger"].log_event(
                    shared, "max_iterations_reached", error=str(exc)
                )
                _console.print(
                    f"\n[bold red]Max iterations reached:[/bold red] {exc}"
                )
            except SuspendExecution as exc:
                shared["logger"].log_event(
                    shared, "session_suspended", checkpoint=exc.checkpoint_path
                )
                _console.print(
                    f"\n[bold yellow]Session suspended.[/bold yellow] "
                    f"Checkpoint: {exc.checkpoint_path}"
                )
                shared["suspended"] = True
                shared["checkpoint_path"] = exc.checkpoint_path
            except Exception as exc:
                shared["logger"].log_event(
                    shared, "unhandled_error", error=str(exc)
                )
                _console.print(f"\n[bold red]Unhandled error:[/bold red] {exc}")
                raise
            finally:
                shared["logger"].log_event(
                    shared,
                    "session_end",
                    total_iterations=shared["iteration"],
                )

        _console.print(Rule("[dim]Session complete[/dim]"))
        return shared

    def _load_agent(self) -> dict:
        path = self.agents_dir / f"{self.agent_id}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Agent definition not found: {path}")
        with path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh)
