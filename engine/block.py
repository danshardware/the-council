"""Block types — each maps to a PocketFlow Node subclass."""

from __future__ import annotations

import sys
import os
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pocketflow import Node
from engine.llm import call_llm
from engine.template import render_prompt, TemplateRenderError
from tools import get_tool, ToolContext

_console = Console()


class MaxIterationsError(Exception):
    pass


class SuspendExecution(Exception):
    """Raised by CheckpointBlock when the agent suspends to wait for an async reply."""
    def __init__(self, checkpoint_path: str, msg: str = "") -> None:
        super().__init__(msg)
        self.checkpoint_path = checkpoint_path


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseBlock(Node):
    def __init__(self, block_id: str, config: dict) -> None:
        super().__init__()
        self.block_id = block_id
        self.config = config

    def _check_iterations(self, shared: dict) -> None:
        shared["iteration"] = shared.get("iteration", 0) + 1
        visits = shared.setdefault("block_visits", {})
        visits[self.block_id] = visits.get(self.block_id, 0) + 1

        max_iter: int = shared.get("max_iterations", 50)
        iteration: int = shared["iteration"]

        # Per-block visit cap (independent of global iteration limit)
        max_visits = self.config.get("max_visits")
        if max_visits and visits[self.block_id] > max_visits:
            raise MaxIterationsError(
                f"Block '{self.block_id}' exceeded max_visits={max_visits}"
            )

        # --- Approaching-limit warning (injected once, ~10 turns before cap) ---
        _WARN_BUFFER = max(3, max_iter // 10)
        if not shared.get("_iteration_warned") and iteration >= max_iter - _WARN_BUFFER:
            shared["_iteration_warned"] = True
            remaining = max_iter - iteration
            shared.setdefault("messages", []).append({
                "role": "user",
                "content": (
                    f"[SYSTEM] Warning: you are approaching the iteration limit. "
                    f"Approximately {remaining} turns remain. Begin consolidating your "
                    "findings and move toward writing your final output now."
                ),
            })

        # --- Grace period: 3 wrap-up turns before hard stop ---
        if iteration > max_iter:
            if not shared.get("_grace_mode"):
                # First overflow — activate grace period
                shared["_grace_mode"] = True
                shared["max_iterations"] = iteration + 2  # activation turn + 2 more = 3 total
                shared.setdefault("messages", []).append({
                    "role": "user",
                    "content": (
                        "[SYSTEM] You have reached the iteration limit. "
                        "You have exactly 3 turns left. "
                        "Write your final output now using whatever information you have "
                        "already gathered — do not start any new tasks. Make sure the to mention you had more work to do if need be."
                    ),
                })
            else:
                # Grace period exhausted → hard stop
                raise MaxIterationsError(
                    f"Max iterations ({max_iter}) reached at block '{self.block_id}'"
                )

    def _default_model(self, shared: dict) -> str:
        return shared["agent_config"]["model_defaults"]["model_id"]

    def _get_bedrock_tools(self, shared: dict) -> list:
        ctx: ToolContext = shared["tool_context"]
        tools = []
        for name in (self.config.get("tools") or []):
            bt = get_tool(name, ctx)
            if bt is not None:
                tools.append(bt)
        return tools

    def _log(self, shared: dict, event: str, **kwargs: Any) -> None:
        shared["logger"].log_event(shared, event, block=self.block_id, **kwargs)


# ---------------------------------------------------------------------------
# LLM block
# ---------------------------------------------------------------------------

class LLMBlock(BaseBlock):
    def prep(self, shared: dict) -> dict:
        self._check_iterations(shared)
        self._log(shared, "block_enter", iteration=shared["iteration"])
        self._model_id = self.config.get("model_id") or self._default_model(shared)
        self._tools = self._get_bedrock_tools(shared)
        return dict(shared)  # pass a snapshot

    def exec(self, prep_res: dict) -> dict:
        import sys
        messages = list(prep_res.get("messages", []))
        system_prompt = render_prompt(self.config["system_prompt"], prep_res)
        _logger = prep_res.get("logger")
        _block_id = self.block_id

        def _tool_callback(tc: dict) -> None:
            if _logger:
                _logger.log_event(prep_res, "tool_use", block=_block_id,
                                  tool=tc["tool"], input=tc["input"], result=tc["result"])

        # Prepend shared context blocks (from agent context_files)
        context_injection: str = prep_res.get("context_injection", "")
        if context_injection:
            system_prompt = context_injection.rstrip() + "\n\n" + system_prompt

        # Inject workspace paths so agent knows where it can write
        allowed_paths = prep_res.get("tool_context") and prep_res["tool_context"].allowed_paths
        if allowed_paths:
            paths_str = ", ".join(f"`{p}`" for p in allowed_paths)
            session_id = prep_res.get("session_id", "")
            session_path = f"{paths_str}/{session_id}" if session_id else paths_str
            system_prompt = system_prompt.rstrip() + f"\n\nYou can access files in: {paths_str}\nYour session working directory is: {session_path}\n"

        # Auto-inject tool schema section so agent knows available tool signatures
        if self._tools:
            lines = ["\n## Available Tools"]
            for bt in self._tools:
                spec = bt.tool_spec
                props = spec.get("inputSchema", {}).get("json", {}).get("properties", {})
                params = ", ".join(
                    f"{k}: {v.get('type', 'string')}" for k, v in props.items()
                )
                lines.append(f"- **{spec['name']}**({params}) — {spec.get('description', '')}")
            system_prompt = system_prompt.rstrip() + "\n" + "\n".join(lines) + "\n"

        is_tty = sys.stdout.isatty()
        if is_tty:
            with _console.status(
                f"[dim]⏳ {self.block_id} → {self._model_id.split('.')[-1]}…[/dim]",
                spinner="dots",
            ):
                parsed, in_tok, out_tok = call_llm(
                    model_id=self._model_id,
                    system_prompt=system_prompt,
                    messages=messages,
                    tools=self._tools or None,
                    tool_callback=_tool_callback,
                )
        else:
            parsed, in_tok, out_tok = call_llm(
                model_id=self._model_id,
                system_prompt=system_prompt,
                messages=messages,
                tools=self._tools or None,
                tool_callback=_tool_callback,
            )
        parsed["_in_tokens"] = in_tok
        parsed["_out_tokens"] = out_tok
        return parsed

    def post(self, shared: dict, prep_res: dict, exec_res: dict) -> str:
        action = exec_res.get("action", "default")
        in_tok = exec_res.pop("_in_tokens", 0)
        out_tok = exec_res.pop("_out_tokens", 0)
        raw_response = exec_res.pop("_raw_response", "")
        exec_res.pop("_tool_calls", [])  # already logged in real-time via tool_callback

        shared["action"] = action
        shared["action_input"] = exec_res.get("action_input", {})

        # Append a clean human-readable summary so conversation history stays useful
        reasoning = exec_res.get("reasoning", "")
        summary = f"[{self.block_id}] action={action}"
        if reasoning:
            summary += f" | {reasoning[:300]}"
        elif raw_response and action == "default":
            # Parsing failed — include raw text so next iteration has some context
            summary += f" | (unparsed) {raw_response[:300]}"
        # Strip to avoid Bedrock validation errors on trailing whitespace
        summary = summary.strip()
        shared["messages"].append({"role": "assistant", "content": summary})

        # Keep conversation history bounded to avoid context bloat (keep first user msg + last 11)
        messages = shared["messages"]
        if len(messages) > 12:
            shared["messages"] = [messages[0]] + messages[-11:]

        # Auto-checkpoint after every LLM turn so resume() has a per-turn snapshot.
        # Best-effort — a failure here must never crash the agent.
        try:
            tc = shared.get("tool_context")
            if tc and getattr(tc, "allowed_paths", None):
                shared["_last_block_id"] = self.block_id
                from engine.state import save_session_checkpoint
                save_session_checkpoint(shared, tc.allowed_paths[0])
        except Exception:
            pass

        self._log(
            shared,
            "llm_call",
            model=self._model_id,
            action=action,
            input_tokens=in_tok,
            output_tokens=out_tok,
            raw_response=raw_response[:2000],
        )
        self._log(shared, "transition", from_block=self.block_id, to_action=action)

        display_text = reasoning[:200] if reasoning else f"[no YAML] {raw_response[:300]}"
        _console.print(
            Panel(
                Text.from_markup(
                    f"[bold cyan]{self.block_id}[/bold cyan]  "
                    f"[yellow]→[/yellow] [bold white]{action}[/bold white]\n"
                    f"[dim]{display_text}[/dim]"
                ),
                title=f"🤖 LLM • iter {shared['iteration']}",
                border_style="green",
            )
        )
        return action


# ---------------------------------------------------------------------------
# Guardrail block
# ---------------------------------------------------------------------------

class GuardrailBlock(BaseBlock):
    def prep(self, shared: dict) -> dict:
        self._check_iterations(shared)
        self._log(shared, "block_enter", iteration=shared["iteration"])
        self._model_id = self.config.get("model_id") or self._default_model(shared)
        return dict(shared)

    def exec(self, prep_res: dict) -> dict:
        import sys
        action = prep_res.get("action", "")
        action_input = prep_res.get("action_input", {})
        user_msg = (
            f"Proposed action: {action}\n"
            f"Action input:\n{yaml.dump(action_input, default_flow_style=False)}"
        )
        system_prompt = render_prompt(self.config["system_prompt"], prep_res)
        if sys.stdout.isatty():
            with _console.status(
                f"[dim]⏳ {self.block_id} → reviewing '{action}'…[/dim]",
                spinner="dots",
            ):
                parsed, in_tok, out_tok = call_llm(
                    model_id=self._model_id,
                    system_prompt=system_prompt,
                    messages=[{"role": "user", "content": user_msg}],
                )
        else:
            parsed, in_tok, out_tok = call_llm(
                model_id=self._model_id,
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
        parsed["_in_tokens"] = in_tok
        parsed["_out_tokens"] = out_tok
        return parsed

    def post(self, shared: dict, prep_res: dict, exec_res: dict) -> str:
        verdict = exec_res.get("verdict", "approved")
        reason = exec_res.get("reason", "")
        in_tok = exec_res.pop("_in_tokens", 0)
        out_tok = exec_res.pop("_out_tokens", 0)

        self._log(
            shared,
            "guardrail",
            verdict=verdict,
            reason=reason,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )

        if verdict != "approved":
            # Inject system message so the agent knows the action was blocked
            shared["messages"].append({
                "role": "user",
                "content": (
                    f"[SYSTEM] Your proposed action '{shared.get('action')}' "
                    f"was {verdict} by the safety guardrail. Reason: {reason}. "
                    "Please reconsider."
                ),
            })

        reviewing_action = prep_res.get("action", "?")
        style = "green" if verdict == "approved" else "red"
        emoji = "✅" if verdict == "approved" else "🚫"
        _console.print(
            Panel(
                f"[dim]reviewing:[/dim] [yellow]{reviewing_action}[/yellow]\n"
                f"{emoji} [bold]{verdict}[/bold] — {reason}",
                title=f"🛡️  Guardrail • {self.block_id}",
                border_style=style,
            )
        )
        return verdict


# ---------------------------------------------------------------------------
# Tool-call block (no LLM — directly invokes a named tool)
# ---------------------------------------------------------------------------

class ToolCallBlock(BaseBlock):
    def prep(self, shared: dict) -> dict:
        self._check_iterations(shared)
        self._log(shared, "block_enter", iteration=shared["iteration"])
        return dict(shared)

    def exec(self, prep_res: dict) -> Any:
        tool_name: str = self.config["tool"]
        ctx: ToolContext = prep_res["tool_context"]
        bt = get_tool(tool_name, ctx)
        if bt is None:
            raise ValueError(f"Tool '{tool_name}' not found in registry")
        action_input: dict = prep_res.get("action_input", {})
        import time
        t0 = time.monotonic()
        try:
            result = bt(**action_input)
        except TypeError as e:
            # LLM called with wrong parameter names/count — return error message
            # so LLM can see and correct itself
            result = f"[ERROR] Tool '{tool_name}' parameter error: {str(e)}\nExpected parameters: {bt.tool_spec['inputSchema']['json']['properties'].keys()}"
        except Exception as e:
            # Other errors — also return as message so LLM sees it
            result = f"[ERROR] Tool '{tool_name}' failed: {str(e)}"
        duration_ms = int((time.monotonic() - t0) * 1000)
        return {"result": result, "duration_ms": duration_ms, "tool": tool_name}

    def post(self, shared: dict, prep_res: dict, exec_res: dict) -> str:
        self._log(
            shared,
            "tool_call",
            tool=exec_res["tool"],
            duration_ms=exec_res["duration_ms"],
        )
        shared["messages"].append({
            "role": "user",
            "content": f"[SYSTEM] Tool '{exec_res['tool']}' result: {exec_res['result']}",
        })
        _console.print(
            Panel(
                f"[bold]{exec_res['tool']}[/bold] [dim]({exec_res['duration_ms']}ms)[/dim]\n"
                f"[dim]{str(exec_res['result'])[:300]}[/dim]",
                title=f"🔧 Tool",
                border_style="blue",
            )
        )
        return "default"


# ---------------------------------------------------------------------------
# Checkpoint block — persists state and optionally suspends the agent
# ---------------------------------------------------------------------------

class CheckpointBlock(BaseBlock):
    def prep(self, shared: dict) -> dict:
        self._log(shared, "checkpoint", mode=self.config.get("mode", "noop"))
        return dict(shared)

    def exec(self, prep_res: dict) -> str | None:
        mode = self.config.get("mode", "noop")
        if mode in ("suspend", "delegate"):
            from engine.state import save_checkpoint, checkpoint_path_for
            cp_path = checkpoint_path_for(
                prep_res.get("logs_dir", "logs"),
                prep_res["agent_id"],
                prep_res["session_id"],
            )
            save_checkpoint(prep_res, cp_path)
            return str(cp_path)
        return None

    def post(self, shared: dict, prep_res: dict, exec_res: str | None) -> str:
        mode = self.config.get("mode", "noop")

        if mode == "delegate" and exec_res:
            target = self.config.get("delegate_to")
            prompt = self.config.get("delegate_prompt") or shared.get("action_input", {}).get("task", "")
            if target and prompt:
                from engine.mailbox import Mailbox
                mailbox = Mailbox()
                mailbox.send(
                    target_agent=target,
                    prompt=str(prompt),
                    from_agent=shared["agent_id"],
                    from_session=shared["session_id"],
                    reply_to_session=shared["session_id"],
                )
                _console.print(
                    Panel(
                        f"Delegated to [bold]{target}[/bold] — session suspended.\n"
                        f"Checkpoint: {exec_res}",
                        title="📬  Checkpoint / Delegate",
                        border_style="yellow",
                    )
                )
            raise SuspendExecution(checkpoint_path=exec_res, msg=f"Delegating to {target}")

        if mode == "suspend" and exec_res:
            _console.print(
                Panel(
                    f"Session suspended. Checkpoint saved:\n{exec_res}",
                    title="💾  Checkpoint / Suspend",
                    border_style="yellow",
                )
            )
            raise SuspendExecution(checkpoint_path=exec_res, msg="Suspended")

        # noop — just log and continue
        _console.print(
            Panel(
                "Checkpoint reached (noop) — continuing.",
                title="💾  Checkpoint",
                border_style="yellow",
            )
        )
        return self.config.get("on_timeout", "default")


# ---------------------------------------------------------------------------
# Human-input block
# ---------------------------------------------------------------------------

class HumanInputBlock(BaseBlock):
    def prep(self, shared: dict) -> dict:
        self._log(shared, "human_input_requested")
        return dict(shared)

    def exec(self, prep_res: dict) -> str:
        prompt = self.config.get("prompt", "Agent requires input [y/n]: ")
        _console.print(f"\n🧑  [bold magenta]Human Input Required:[/bold magenta] {prompt}", end="")
        response = input().strip().lower()
        return response

    def post(self, shared: dict, prep_res: dict, exec_res: str) -> str:
        verdict = "approved" if exec_res in ("y", "yes", "approved") else "rejected"
        self._log(shared, "human_input_received", verdict=verdict, raw=exec_res)
        shared["messages"].append({
            "role": "user",
            "content": f"[HUMAN] Response to confirmation request: {verdict}",
        })
        return verdict


# ---------------------------------------------------------------------------
# Human-reply block — free-text round-trip with the user
# ---------------------------------------------------------------------------

class HumanReplyBlock(BaseBlock):
    """Displays the agent's message and reads a free-text reply from the user."""

    def prep(self, shared: dict) -> dict:
        self._log(shared, "human_input_requested")
        return dict(shared)

    def exec(self, prep_res: dict) -> str:
        action_input = prep_res.get("action_input", {})
        if isinstance(action_input, dict):
            message = action_input.get("message", "")
        else:
            message = str(action_input)
        if message:
            _console.print(f"\n🤖 [bold cyan]Agent:[/bold cyan] {message}")
        _console.print("🧑  [bold magenta]You:[/bold magenta] ", end="")
        return input().strip()

    def post(self, shared: dict, prep_res: dict, exec_res: str) -> str:
        self._log(shared, "human_reply", text=exec_res)
        shared["messages"].append({"role": "user", "content": f"[HUMAN] {exec_res}"})
        return "replied"


# ---------------------------------------------------------------------------
# SetState block — writes a value from shared into another shared key
# ---------------------------------------------------------------------------

_FORBIDDEN_WRITE_KEYS: frozenset[str] = frozenset({
    "logger",
    "tool_context",
    "agent_config",
    "messages",
    "iteration",
    "block_visits",
    "max_iterations",
    "session_id",
    "agent_id",
    "logs_dir",
})


def _get_nested(obj: Any, path: str) -> Any:
    """Traverse obj using dot-notation. Raises KeyError if any segment is missing."""
    for part in path.split("."):
        if isinstance(obj, dict):
            if part not in obj:
                raise KeyError(f"Key '{part}' not found (path: '{path}')")
            obj = obj[part]
        elif isinstance(obj, list):
            try:
                obj = obj[int(part)]
            except (ValueError, IndexError) as exc:
                raise KeyError(f"Index '{part}' invalid (path: '{path}')") from exc
        else:
            raise KeyError(
                f"Cannot traverse into '{type(obj).__name__}' at '{part}' (path: '{path}')"
            )
    return obj


def _set_nested(obj: dict, path: str, value: Any, merge: bool) -> None:
    """Write value into a nested dict using dot-notation, creating intermediate dicts."""
    parts = path.split(".")
    root = parts[0]
    if root in _FORBIDDEN_WRITE_KEYS or root.startswith("_"):
        raise ValueError(f"Writing to state key '{root}' is not allowed")
    # Traverse to parent container
    for part in parts[:-1]:
        if part not in obj or not isinstance(obj[part], dict):
            obj[part] = {}
        obj = obj[part]
    leaf = parts[-1]
    existing = obj.get(leaf)
    if merge and isinstance(existing, dict) and isinstance(value, dict):
        existing.update(value)
    else:
        obj[leaf] = value


class SetStateBlock(BaseBlock):
    """
    Writes a value from shared state (via a dot-notation source path) to another
    shared state key (dot-notation target path).

    Config fields:
        key     (required) — dot-notation write target in shared
        source  (optional) — dot-notation read path in shared
                             defaults to: action_input.<leaf of key>
        merge   (optional) — for dict values, merge into existing dict (default: true)

    Transitions:
        set   — value was resolved and is non-empty/non-None
        empty — value is None, "", [], or {}
        error — source path not found (only if wired; otherwise raises)
    """

    def prep(self, shared: dict) -> dict:
        self._check_iterations(shared)
        self._log(shared, "block_enter", iteration=shared["iteration"])
        return dict(shared)

    def exec(self, prep_res: dict) -> dict:
        key: str = self.config["key"]
        default_source = f"action_input.{key.split('.')[-1]}"
        source: str = self.config.get("source") or default_source
        merge: bool = self.config.get("merge", True)

        try:
            value = _get_nested(prep_res, source)
        except KeyError as exc:
            if "error" in self.config.get("transitions", {}):
                return {"_transition": "error", "_error": str(exc)}
            raise

        return {"_key": key, "_value": value, "_merge": merge}

    def post(self, shared: dict, prep_res: dict, exec_res: dict) -> str:
        if exec_res.get("_transition") == "error":
            err = exec_res["_error"]
            self._log(shared, "set_state_error", error=err)
            _console.print(
                Panel(
                    f"[red]Source not found:[/red] {err}",
                    title=f"📝  SetState • {self.block_id}",
                    border_style="red",
                )
            )
            return "error"

        key: str = exec_res["_key"]
        value: Any = exec_res["_value"]
        merge: bool = exec_res["_merge"]

        _set_nested(shared, key, value, merge)
        self._log(shared, "set_state", key=key, value=str(value)[:200])

        is_empty = value is None or value == "" or value == [] or value == {}
        transition = "empty" if is_empty else "set"

        _console.print(
            Panel(
                f"[bold]{key}[/bold] ← {repr(value)[:200]}\n[dim]→ {transition}[/dim]",
                title=f"📝  SetState • {self.block_id}",
                border_style="dim" if is_empty else "cyan",
            )
        )
        return transition



BLOCK_TYPES = {
    "llm": LLMBlock,
    "guardrail": GuardrailBlock,
    "tool_call": ToolCallBlock,
    "checkpoint": CheckpointBlock,
    "human_input": HumanInputBlock,
    "human_reply": HumanReplyBlock,
    "set_state": SetStateBlock,
}


def make_block(block_id: str, config: dict) -> BaseBlock:
    block_type: str = config.get("type") or ""
    cls = BLOCK_TYPES.get(block_type)
    if cls is None:
        raise ValueError(f"Unknown block type '{block_type}' for block '{block_id}'")
    return cls(block_id, config)
