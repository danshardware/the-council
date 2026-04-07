"""Agent state serialisation — checkpoint shared state to/from disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_SKIP_KEYS = {"logger", "tool_context"}


def save_checkpoint(shared: dict, checkpoint_path: str | Path) -> None:
    """Serialise shared state (excluding unpicklable objects) to a JSON file."""
    path = Path(checkpoint_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    serialisable = {k: v for k, v in shared.items() if k not in _SKIP_KEYS}
    with path.open("w", encoding="utf-8") as fh:
        json.dump(serialisable, fh, indent=2, default=str)


def load_checkpoint(checkpoint_path: str | Path) -> dict[str, Any]:
    """Load a previously saved checkpoint. Returns the raw dict (caller re-attaches live objects)."""
    path = Path(checkpoint_path)
    if not path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def checkpoint_path_for(logs_dir: str, agent_id: str, session_id: str) -> Path:
    return Path(logs_dir) / agent_id / f"{session_id}_checkpoint.json"
