"""AgentRunner — loads an agent definition + flow and drives execution."""

from __future__ import annotations

import json
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
        prior_messages: list | None = None,
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

        # Session-scoped workspace: workspace/ceo/ → workspace/ceo/<session_id>/
        # This prevents file clashes when the same agent runs concurrently.
        _base_paths = agent_config.get("permissions", {}).get("workspace_paths", [])
        session_workspace_paths = [
            str(Path(p.rstrip("/")) / session_id) + "/"
            for p in _base_paths
        ]
        for _sp in session_workspace_paths:
            Path(_sp).mkdir(parents=True, exist_ok=True)

        # Build shared state
        # When resuming, seed the conversation with prior history so the agent
        # can continue without repeating work already done.
        initial_messages: list = prior_messages if prior_messages else [{"role": "user", "content": prompt}]
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
            "messages": initial_messages,
            "initial_prompt": prompt,
            "context_injection": _load_context_files(agent_config),
            "logger": Logger(str(self.logs_dir), self.agent_id, session_id),
            "tool_context": ToolContext(
                agent_id=self.agent_id,
                session_id=session_id,
                allowed_paths=session_workspace_paths,
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
                flow_name=flow_name,
                prompt=prompt,
                resumed=prior_messages is not None,
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

        # Post-session: summarise conversation + reconcile facts into memory
        if agent_config.get("post_session_flow") and not shared.get("suspended"):
            from engine.post_session_runner import PostSessionRunner
            PostSessionRunner().run_after_session(shared)

        return shared

    def resume(self, session_id: str) -> dict:
        """Resume a crashed or incomplete session.

        Recovery order:
        1. Latest timestamped checkpoint from <workspace>/_checkpoints/ (richest state)
        2. `messages` snapshot from the last session_end in the JSONL log (fallback)

        In both cases the workspace file listing is injected as a [SYSTEM] message
        so the agent knows exactly what it already produced and can continue without
        re-doing completed work.  The iteration counter always resets to 0 — the
        agent gets a fresh budget.
        """
        log_path = self.logs_dir / self.agent_id / f"{session_id}.jsonl"
        if not log_path.exists():
            raise FileNotFoundError(
                f"No log found for session '{session_id}' "
                f"(looked in {log_path})"
            )

        events: list[dict] = []
        with log_path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    events.append(json.loads(line))

        start_event = next((e for e in events if e["event"] == "session_start"), None)
        if start_event is None:
            raise ValueError(f"No session_start found in log for '{session_id}'")

        prompt: str = start_event["prompt"]
        flow_name: str = start_event.get("flow_name", "main")

        # Derive session workspace path (same logic as run())
        agent_config = self._load_agent()
        _base_paths = agent_config.get("permissions", {}).get("workspace_paths", [])
        session_workspace = Path(_base_paths[0].rstrip("/")) / session_id if _base_paths else None

        # --- 1. Try latest workspace checkpoint ---
        prior_messages: list | None = None
        checkpoint_source = "none"
        if session_workspace:
            from engine.state import latest_session_checkpoint, load_checkpoint as _load_cp
            cp_path = latest_session_checkpoint(session_workspace)
            if cp_path:
                try:
                    cp_data = _load_cp(cp_path)
                    prior_messages = cp_data.get("messages")
                    checkpoint_source = cp_path.name
                except Exception as exc:
                    _console.print(f"[yellow]Warning:[/yellow] could not load checkpoint {cp_path}: {exc}")

        # --- 2. Fall back to JSONL session_end snapshot ---
        if not prior_messages:
            snapshot_event = next(
                (e for e in reversed(events)
                 if e["event"] in ("session_end", "unhandled_error") and "messages" in e),
                start_event,
            )
            prior_messages = snapshot_event.get("messages") or [{"role": "user", "content": prompt}]
            checkpoint_source = f"jsonl:{snapshot_event['event']}"

        # --- 3. Inject workspace file listing so agent knows what it already made ---
        if session_workspace:
            from engine.state import workspace_file_summary
            summary = workspace_file_summary(session_workspace)
            if summary:
                prior_messages = list(prior_messages)  # ensure mutable copy
                prior_messages.append({
                    "role": "user",
                    "content": (
                        "[SYSTEM] Resuming previous session. "
                        "The following files already exist in your workspace from prior work — "
                        "do NOT redo research that is already captured here. "
                        "Review these and continue from where you left off:\n\n"
                        + summary
                    ),
                })

        _console.print(
            f"[bold yellow]Resuming session[/bold yellow] [dim]{session_id}[/dim]  "
            f"[dim](source: {checkpoint_source} | {len(prior_messages)} messages)[/dim]"
        )

        return self.run(
            prompt=prompt,
            flow_name=flow_name,
            session_id=session_id,
            prior_messages=prior_messages,
        )

    def _load_agent(self) -> dict:
        path = self.agents_dir / f"{self.agent_id}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Agent definition not found: {path}")
        with path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh)


def _load_context_files(agent_config: dict) -> str:
    """Read files matching context_files globs from agent config and return XML-tagged blocks."""
    import glob as _glob
    entries: list[dict] = agent_config.get("context_files", [])
    if not entries:
        return ""
    parts: list[str] = []
    for entry in entries:
        pattern = entry.get("glob", "")
        tag = entry.get("tag", "context")
        if not pattern:
            continue
        matched = sorted(_glob.glob(pattern, recursive=True))
        if not matched:
            continue
        chunks: list[str] = []
        for fpath in matched:
            try:
                with open(fpath, encoding="utf-8") as fh:
                    chunks.append(fh.read().strip())
            except UnicodeDecodeError:
                with open(fpath, encoding="latin-1") as fh:
                    chunks.append(fh.read().strip())
            except OSError:
                pass
        if chunks:
            parts.append(f"<{tag}>\n" + "\n\n".join(chunks) + f"\n</{tag}>")
    return "\n\n".join(parts)
