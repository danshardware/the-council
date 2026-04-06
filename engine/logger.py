import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Logger:
    def __init__(self, logs_dir: str, agent_id: str, session_id: str) -> None:
        self.agent_id = agent_id
        self.session_id = session_id
        log_dir = Path(logs_dir) / agent_id
        log_dir.mkdir(parents=True, exist_ok=True)
        self._fh = open(log_dir / f"{session_id}.jsonl", "a", buffering=1)

    def log_event(self, shared: dict, event: str, **kwargs: Any) -> None:
        record = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent_id": shared["agent_id"],
            "session_id": shared["session_id"],
            "event": event,
            **kwargs,
        }
        self._fh.write(json.dumps(record) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.flush()
        self._fh.close()

    def __enter__(self) -> "Logger":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
