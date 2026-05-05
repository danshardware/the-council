# C2 — Tool Discovery Tools

## Overview

Add two new tools to the registry so agents (especially Agent Creator) can
discover what tools exist and find relevant ones by semantic description:

1. `list_tools` — returns the full list of registered tool names and their
   one-line descriptions
2. `search_tools` — given a natural language query, returns the subset of tools
   relevant to that domain (e.g. "file operations", "web browsing", "scheduling")

`search_tools` uses an LLM (Nova Lite) to do the matching — given the small tool
count, this is simpler and more flexible than embeddings.

Both tools require no file permissions and work from the in-memory registry.

---

## Type Contracts

### `list_tools`

```python
@tool
def list_tools(context: ToolContext) -> str:
    """
    List all registered tools with their name and description.

    Returns a formatted string: one tool per line in the format:
      <name>: <description>
    """
```

Return format:

```
read_file: Read a text file and return its contents.
write_file: Write content to a file, creating parent directories if needed.
run_command: Run a shell command and return its stdout + stderr. ...
...
```

### `search_tools`

```python
@tool
def search_tools(query: str, context: ToolContext) -> str:
    """
    Search registered tools by semantic description.

    Returns the subset of tools relevant to `query`, with their names
    and descriptions. Uses an LLM to assess relevance.

    Example queries:
      "file reading and writing"
      "web browsing and scraping"
      "memory storage and retrieval"
      "scheduling and timing"
    """
```

Return format: same as `list_tools` but filtered to relevant tools only.

---

## Workflow

### `list_tools` implementation

```python
from tools import _REGISTRY

@tool
def list_tools(context: ToolContext) -> str:
    lines = []
    for name, func in sorted(_REGISTRY.items()):
        doc = (func.__doc__ or "No description.").strip().split("\n")[0]
        lines.append(f"{name}: {doc}")
    return "\n".join(lines) if lines else "(no tools registered)"
```

### `search_tools` implementation

```python
from engine.llm import call_llm

@tool
def search_tools(query: str, context: ToolContext) -> str:
    # Build the full tool listing
    all_tools = []
    for name, func in sorted(_REGISTRY.items()):
        doc = (func.__doc__ or "No description.").strip().split("\n")[0]
        all_tools.append(f"{name}: {doc}")
    tool_list = "\n".join(all_tools)

    system_prompt = (
        "You are a tool catalogue assistant. Given a list of tools and a query, "
        "return ONLY the tools that are relevant to the query. "
        "Do not explain — return one tool per line in the format 'name: description'. "
        "If no tools match, return '(no matching tools)'."
    )
    user_msg = f"Query: {query}\n\nAvailable tools:\n{tool_list}"

    parsed_raw, _, _ = call_llm(
        model_id="us.amazon.nova-lite-v1:0",
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": user_msg}],
    )
    # call_llm returns a parsed YAML dict — but this response is plain text.
    # Use _raw_response instead.
    return parsed_raw.get("_raw_response", "(error: no response)")
```

**Note**: `call_llm` parses YAML by default.  Since `search_tools` expects plain
text back, the implementation may need to use a raw Bedrock call or handle the
`_raw_response` field.  Investigate `call_llm`'s return for plain-text responses
and adjust accordingly — it may be simplest to format the system prompt to instruct
the model to respond in YAML with a `results:` key.

Alternative approach (simpler, no LLM cost):

```python
# Keyword-based fallback if LLM approach is complex:
@tool
def search_tools(query: str, context: ToolContext) -> str:
    query_lower = query.lower()
    query_words = set(query_lower.split())
    results = []
    for name, func in sorted(_REGISTRY.items()):
        doc = (func.__doc__ or "").lower()
        if any(word in name.lower() or word in doc for word in query_words):
            first_line = (func.__doc__ or "No description.").strip().split("\n")[0]
            results.append(f"{name}: {first_line}")
    return "\n".join(results) if results else "(no matching tools)"
```

**Recommendation**: Start with keyword-based (zero LLM cost, zero latency, no
complexity).  The tool set is small enough that keyword matching is sufficient.
If it proves insufficient, upgrade to LLM-based in a follow-up.

---

## Where to Add the Tools

New file: `tools/registry_tools.py`

```python
"""Tool discovery tools — list and search the registered tool registry."""
from __future__ import annotations
from tools import ToolContext, tool, _REGISTRY
```

Add to the tool imports in `engine/runner.py` (or wherever tools are imported at
startup) to ensure auto-registration.  Check how existing tool modules are loaded —
if they rely on import side effects, `registry_tools.py` must be imported too.

---

## Testing Plan (TDD)

File: `tests/test_tool_discovery.py`

```python
def test_list_tools_returns_all_registered():
    # Import all tool modules to ensure registration
    import tools.file_tools, tools.memory_tools, tools.schedule_tools
    ctx = make_test_context()
    result = list_tools(ctx)
    assert "read_file" in result
    assert "write_file" in result
    assert "store_memory" in result

def test_list_tools_format():
    ctx = make_test_context()
    result = list_tools(ctx)
    for line in result.splitlines():
        assert ": " in line, f"Bad format: {line!r}"

def test_search_tools_file_query():
    ctx = make_test_context()
    result = search_tools("file reading and writing", ctx)
    assert "read_file" in result
    assert "write_file" in result

def test_search_tools_memory_query():
    ctx = make_test_context()
    result = search_tools("memory storage", ctx)
    assert "store_memory" in result or "search_memory" in result

def test_search_tools_no_match():
    ctx = make_test_context()
    result = search_tools("quantum entanglement", ctx)
    assert "no matching tools" in result.lower() or result == ""

def test_search_tools_networking_returns_command_tool():
    ctx = make_test_context()
    result = search_tools("networking ping", ctx)
    assert "run_command" in result
```

---

## Acceptance Criteria

- [ ] `tools/registry_tools.py` exists with `list_tools` and `search_tools` decorated
      with `@tool`
- [ ] Both tools are imported at startup (auto-registered)
- [ ] `list_tools` returns all registered tools, one per line, `name: description` format
- [ ] `search_tools("file operations")` returns at least `read_file` and `write_file`
- [ ] `search_tools("networking")` returns `run_command`
- [ ] `search_tools` with no matching query returns a clear empty result
- [ ] All tests pass

---

## Agent YAML Updates

Add `list_tools` and `search_tools` to Agent Creator's available tools:

```yaml
# agents/agent_creator.yaml  — add to relevant blocks in agent_creator_loop.yaml
# tools: [list_tools, search_tools, read_file, write_file, ...]
```

Also add to Concierge and Ops as useful introspection tools.

---

## QA Notes

- `_REGISTRY` is a module-level dict in `tools/__init__.py`.  It's populated by
  `@tool` decorator side effects at import time.  If a tool module isn't imported,
  its tools aren't in the registry.  Confirm all tool modules are imported before
  `list_tools` is called in tests.
- The keyword approach means `search_tools("schedule")` will match `schedule_agent`,
  `list_schedules`, `cancel_schedule` — which is correct.
- Do NOT expose `ToolContext` internals (allowed_paths, session_id, etc.) through
  these tools.

---

## Instructions to the Coder

1. Create `tools/registry_tools.py` with both tools.
2. Start with the keyword-based `search_tools` — upgrade later if needed.
3. Ensure the module is imported at startup.
4. Add both tools to `agent_creator_loop.yaml` blocks that design agents.
5. Add both tools to `ops_loop.yaml` plan block.
6. Run tests.
