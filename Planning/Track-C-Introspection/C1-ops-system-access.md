# C1 — Ops System-Wide Read Access + Sensitive File Blocking

## Overview

Ops currently has `read_paths` scoped to `agents/`, `flows/`, `config/`, `docs/`.
To do its job (diagnose issues, inspect code, read logs), it needs read access to
the entire system root.

At the same time, the existing `_assert_path_allowed` in `file_tools.py` only blocks
paths by `_` / `.` prefix convention.  Before widening Ops' access, add a denylist
of sensitive filenames (`.env`, `*.key`, `*.pem`, etc.) to the path guard.

The same denylist applies to ALL agents, not just Ops.

---

## Part 1 — Sensitive File Denylist in `file_tools.py`

### Type Contracts

```python
_SENSITIVE_PATTERNS: frozenset[str]
# Set of glob patterns matched against the filename (not the full path).
# If matched, access is denied regardless of allowed_paths.

def _is_sensitive_file(path: Path) -> bool:
    """Return True if the filename matches a known-sensitive pattern."""
    ...
```

### Sensitive pattern list

```python
_SENSITIVE_PATTERNS: frozenset[str] = frozenset({
    ".env",
    ".env.*",          # .env.local, .env.production, etc.
    "*.key",
    "*.pem",
    "*.p12",
    "*.pfx",
    "*.crt",           # certificates — may contain private keys
    "*.secret",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "*.kdbx",          # KeePass
    "credentials",     # AWS credentials file
    "config",          # AWS config file (catches ~/.aws/config)
})
```

### Implementation

Add `_is_sensitive_file()` to `file_tools.py`:

```python
import fnmatch

def _is_sensitive_file(path: Path) -> bool:
    name = path.name
    return any(fnmatch.fnmatch(name, pattern) for pattern in _SENSITIVE_PATTERNS)
```

Update `_assert_path_allowed()` to also check:

```python
if _is_sensitive_file(resolved):
    raise PermissionError(
        f"Path '{path}' refers to a sensitive file that agents cannot access."
    )
```

This check runs AFTER the allowed_paths check — so the path must be permitted AND
non-sensitive.

---

## Part 2 — Ops Agent YAML: Expand `read_paths`

In `agents/ops.yaml`, update `permissions.read_paths` to include the repo root and
runtime data directories:

```yaml
permissions:
  read_paths:
    - "."                        # repo root (engine/, tools/, pocketflow/, etc.)
    - agents/
    - flows/
    - config/
    - docs/
    - data/logs/
    - data/workspace/
    - data/config/
    - data/shared_knowledge/
```

The `.` entry gives read access to the entire repo root.  `_assert_path_allowed`
resolves relative paths to absolute — confirm this works correctly for `.`.

**Important**: `write_paths` are unchanged — Ops writes only to `data/agents/`,
`data/flows/`, `data/config/`, `data/shared_knowledge/ops/`.

### Path resolution check

In `runner.py`, `_resolve_path(".")` must resolve to the repo root, not `DATA_DIR`.
Paths that don't start with `data/` are returned unchanged (already the case per
existing code).  Confirm `Path(".").resolve()` inside `_assert_path_allowed` matches
correctly against the resolved allowed path.

---

## Part 3 — `command_tools.py`: Block Sensitive Path Arguments

`_assert_command_allowed()` currently only checks executable names.  Commands like
`cat .env`, `grep -r password`, `find . -name "*.key"` pass through unchecked.

Add a secondary check that scans command arguments for sensitive path patterns:

```python
_SENSITIVE_ARG_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r'\.env(\b|$|\.)'),          # .env, .env.local
    re.compile(r'\b\.aws\b'),               # .aws directory
    re.compile(r'\b(id_rsa|id_ed25519)\b'), # SSH keys
    re.compile(r'\.pem\b'),                 # PEM files
    re.compile(r'\.key\b'),                 # key files
)

def _assert_no_sensitive_args(command: str) -> None:
    """Raise PermissionError if the command references sensitive paths."""
    for pattern in _SENSITIVE_ARG_PATTERNS:
        if pattern.search(command):
            raise PermissionError(
                f"Command references a sensitive path or file: {command!r}"
            )
```

Call `_assert_no_sensitive_args(command)` inside `run_command()`, after
`_assert_command_allowed()`.

---

## Testing Plan (TDD)

File: `tests/test_ops_access_and_path_safety.py`

```python
# Part 1 — file_tools denylist
def test_read_env_file_blocked():
    ctx = make_test_context(allowed_paths=["/"])
    result = read_file(".env", ctx)
    assert "[ERROR]" in result

def test_read_pem_file_blocked():
    ctx = make_test_context(allowed_paths=["/"])
    result = read_file("server.pem", ctx)
    assert "[ERROR]" in result

def test_read_normal_file_allowed():
    ctx = make_test_context(allowed_paths=["d:/dev/Council/"])
    result = read_file("d:/dev/Council/README.md", ctx)
    assert "[ERROR]" not in result

# Part 2 — Ops can read engine source
def test_ops_can_read_engine_block():
    runner = AgentRunner(agent_id="ops")
    shared = runner.run(prompt="Read engine/block.py and tell me how many block types exist.")
    messages = [m["content"] for m in shared["messages"] if m["role"] == "assistant"]
    assert any("block" in m.lower() for m in messages)

# Part 3 — command tool denylist
def test_cat_env_blocked():
    ctx = make_test_context(allowed_commands=["cat"])
    result = run_command("cat .env", ctx)
    assert "[ERROR]" in result

def test_grep_aws_blocked():
    ctx = make_test_context(allowed_commands=["grep"])
    result = run_command("grep -r password .aws/", ctx)
    assert "[ERROR]" in result

def test_grep_normal_command_allowed():
    ctx = make_test_context(allowed_commands=["grep"])
    result = run_command("grep -r 'def make_block' engine/", ctx)
    assert "[ERROR]" not in result
```

---

## Acceptance Criteria

- [ ] `_SENSITIVE_PATTERNS` frozenset defined in `file_tools.py`
- [ ] `_is_sensitive_file()` function in `file_tools.py`
- [ ] `_assert_path_allowed()` calls `_is_sensitive_file()` and raises `PermissionError`
- [ ] `_SENSITIVE_ARG_PATTERNS` and `_assert_no_sensitive_args()` in `command_tools.py`
- [ ] `run_command()` calls `_assert_no_sensitive_args()` after executable check
- [ ] Ops `agents/ops.yaml` `read_paths` includes `.` (repo root) and `data/logs/`,
      `data/workspace/`, `data/config/`, `data/shared_knowledge/`
- [ ] All tests pass
- [ ] Ops `write_paths` unchanged

---

## QA Notes

- The `"config"` pattern in `_SENSITIVE_PATTERNS` is intentionally broad — it matches
  `~/.aws/config`.  It will also match any file literally named `config` (with no
  extension).  This is acceptable: agent-readable config files use `.yaml` extensions.
- `_assert_path_allowed` already runs before the sensitive check — a path outside
  allowed_paths is caught first.  The sensitive check is a second layer.
- When Ops reads `engine/block.py`, it uses the existing `read_file` tool.  Confirm
  the resolved path for `.` (repo root) covers the `engine/` subdirectory.
- The command arg check is pattern-based, not exhaustive.  An agent could still run
  `find . -name "secrets.txt"` — that's acceptable.  We're blocking the obvious cases.

---

## Instructions to the Coder

1. Open `tools/file_tools.py`.
2. Add `_SENSITIVE_PATTERNS` as a module-level frozenset.
3. Add `_is_sensitive_file()` using `fnmatch`.
4. Update `_assert_path_allowed()` to call `_is_sensitive_file()`.
5. Open `tools/command_tools.py`.
6. Add `_SENSITIVE_ARG_PATTERNS` and `_assert_no_sensitive_args()`.
7. Call `_assert_no_sensitive_args()` from `run_command()`.
8. Open `agents/ops.yaml`.  Update `read_paths`.
9. Run all tests.
