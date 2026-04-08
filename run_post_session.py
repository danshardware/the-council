#!/usr/bin/env python
"""Run post-session memory consolidation on an existing session log file.

Usage:
    uv run run_post_session.py logs/ceo/17d85a647bff.jsonl
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from engine.post_session_runner import PostSessionRunner

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run run_post_session.py <log_path>")
        sys.exit(1)

    log_path = Path(sys.argv[1])
    PostSessionRunner().run_on_log(log_path)
