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


@tool
def read_file_lines(path: str, start_line: int, end_line: int, context: ToolContext) -> str:
    """Read a specific range of lines from a file. Lines are 1-based and inclusive.
    Useful for inspecting a section of a large file without loading all of it."""
    resolved = _assert_path_allowed(path, context)
    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {path}")
    try:
        text = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = resolved.read_text(encoding="latin-1")
    lines = text.splitlines()
    total = len(lines)
    s = max(1, start_line) - 1
    e = min(total, end_line)
    selected = lines[s:e]
    return "\n".join(f"{s + 1 + i}: {line}" for i, line in enumerate(selected))


@tool
def append_to_file(path: str, content: str, context: ToolContext) -> str:
    """Append content to a file without overwriting it. Creates the file if it does not exist."""
    resolved = _assert_path_allowed(path, context)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("a", encoding="utf-8") as f:
        f.write(content)
    return f"Appended to: {path}"


@tool
def replace_in_file(path: str, old_string: str, new_string: str, context: ToolContext) -> str:
    """Replace exactly one occurrence of old_string with new_string in a file.
    Fails if the string is not found or appears more than once — add more surrounding
    context to old_string to make it unique."""
    resolved = _assert_path_allowed(path, context)
    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {path}")
    try:
        text = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = resolved.read_text(encoding="latin-1")
    count = text.count(old_string)
    if count == 0:
        raise ValueError(f"String not found in {path}")
    if count > 1:
        raise ValueError(
            f"String appears {count} times in {path} — must be unique. "
            "Include more surrounding context in old_string."
        )
    resolved.write_text(text.replace(old_string, new_string, 1), encoding="utf-8")
    return f"Replaced 1 occurrence in: {path}"


@tool
def insert_at_line(path: str, line_number: int, text: str, context: ToolContext) -> str:
    """Insert text before a given 1-based line number in a file.
    Use line_number=1 to prepend. Use line_number equal to (total lines + 1) to append."""
    resolved = _assert_path_allowed(path, context)
    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {path}")
    try:
        content = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = resolved.read_text(encoding="latin-1")
    lines = content.splitlines(keepends=True)
    idx = max(0, min(line_number - 1, len(lines)))
    insert_text = text if text.endswith("\n") else text + "\n"
    lines.insert(idx, insert_text)
    resolved.write_text("".join(lines), encoding="utf-8")
    return f"Inserted at line {line_number} in: {path}"
