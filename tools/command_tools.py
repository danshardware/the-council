from __future__ import annotations

import re
import subprocess
import shlex
from tools import ToolContext, tool


# Shell operators that delimit sub-commands
_SUBCOMMAND_SPLIT = re.compile(r'&&|\|\||[;|]')


def _assert_command_allowed(command: str, context: ToolContext) -> None:
    """Raise PermissionError if any executable in a chained command is not allowed.

    Splits on shell operators (&&, ||, ;, |) and checks the first token of each
    resulting sub-command against the allowlist. This ensures that chained
    commands like `git add -A && git commit -m "..."` are fully validated.
    """
    if not context.allowed_commands:
        raise PermissionError(
            "No commands are allowed for this agent. "
            "Add executables to 'permissions.allowed_commands' in the agent YAML."
        )
    for part in _SUBCOMMAND_SPLIT.split(command):
        part = part.strip()
        if not part:
            continue
        try:
            tokens = shlex.split(part)
        except ValueError:
            raise PermissionError(f"Could not parse command fragment: {part!r}")
        if not tokens:
            continue
        executable = tokens[0]
        if executable not in context.allowed_commands:
            raise PermissionError(
                f"Command '{executable}' is not in the allowed list: {context.allowed_commands}"
            )


@tool
def run_command(command: str, context: ToolContext) -> str:
    """Run a shell command and return its stdout + stderr. Only allowed executables may be used.
    Chained commands using &&, ||, ;, or | are supported — each executable is checked.
    """
    _assert_command_allowed(command, context)
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    output = result.stdout
    if result.stderr:
        output += f"\n[stderr]\n{result.stderr}"
    if result.returncode != 0:
        output += f"\n[exit code: {result.returncode}]"
    return output or "(no output)"
