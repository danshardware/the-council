from __future__ import annotations

import subprocess
import shlex
from tools import ToolContext, tool


def _assert_command_allowed(command: str, context: ToolContext) -> None:
    """Raise PermissionError if the command's executable is not in allowed_commands."""
    if not context.allowed_commands:
        raise PermissionError(
            "No commands are allowed for this agent. "
            "Add executables to 'permissions.allowed_commands' in the agent YAML."
        )
    executable = shlex.split(command)[0]
    if executable not in context.allowed_commands:
        raise PermissionError(
            f"Command '{executable}' is not in the allowed list: {context.allowed_commands}"
        )


@tool
def run_command(command: str, context: ToolContext) -> str:
    """Run a shell command and return its stdout + stderr. Only allowed executables may be used."""
    _assert_command_allowed(command, context)
    result = subprocess.run(
        shlex.split(command),
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout
    if result.stderr:
        output += f"\n[stderr]\n{result.stderr}"
    if result.returncode != 0:
        output += f"\n[exit code: {result.returncode}]"
    return output or "(no output)"
