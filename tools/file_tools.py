from __future__ import annotations
import os
from pathlib import Path
from tools import ToolContext, tool


def _assert_path_allowed(path: str, context: ToolContext) -> Path:
    """Resolve path and verify it is under one of context.allowed_paths. Raises PermissionError if not."""
    resolved = Path(path).resolve()
    for allowed in context.allowed_paths:
        if resolved.is_relative_to(Path(allowed).resolve()):
            return resolved
    raise PermissionError(f"Path '{path}' is outside allowed paths: {context.allowed_paths}")


@tool
def read_file(path: str, context: ToolContext) -> str:
    """Read a text file and return its contents."""
    resolved = _assert_path_allowed(path, context)
    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {path}")
    try:
        return resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return resolved.read_text(encoding="latin-1")


@tool
def write_file(path: str, content: str, context: ToolContext) -> str:
    """Write content to a file, creating parent directories if needed."""
    resolved = _assert_path_allowed(path, context)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return f"Written: {path}"


@tool
def list_files(path: str, context: ToolContext) -> str:
    """List files in a directory. Returns newline-separated relative paths."""
    resolved = _assert_path_allowed(path, context)
    paths = []
    for root, _, files in os.walk(resolved):
        for filename in files:
            full = Path(root) / filename
            paths.append(str(full.relative_to(resolved)))
    return "\n".join(paths) if paths else "(empty)"

@tool
def delete_file(path: str, context: ToolContext) -> str:
    """Delete a file."""
    resolved = _assert_path_allowed(path, context)
    resolved.unlink()
    return f"Deleted: {path}"


@tool
def file_exists(path: str, context: ToolContext) -> str:
    """Check if a file exists. Returns 'true' or 'false'."""
    resolved = _assert_path_allowed(path, context)
    return str(resolved.exists()).lower()
