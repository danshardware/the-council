# How to add tools

---

## Where tools live

All tool files are in `tools/`. `tools/__init__.py` contains `_load_all_tools()` which globs every `*.py` in the directory at startup and imports them, triggering `@tool` registration. **Just drop a new `.py` file in `tools/` and it will be picked up automatically — no manifest entry needed.**

---

## The `@tool` decorator

```python
from tools import ToolContext, tool

@tool
def my_tool(param_one: str, param_two: int, context: ToolContext) -> str:
    """One sentence description. This becomes the tool description Bedrock sees."""
    # implementation
    return "result as a string"
```

Rules:
- Last parameter must be `context: ToolContext`. It is stripped from the Bedrock schema automatically so the LLM never sees it.
- Type annotations on non-context parameters are used to build the JSON schema (`str→string`, `int→integer`, `float→number`, `bool→boolean`, `dict→object`, `list→array`). Annotate everything.
- Return a `str`. If you return a `dict`, the framework serialises it as JSON. Bedrock requires tool results to be string or JSON; return string by default.
- The docstring is the description Bedrock and the LLM see. Make it accurate and specific — the LLM uses it to decide when and how to call the tool.
- Raise exceptions freely; the runner catches them, injects an error message into the conversation, and returns to the previous LLM block.

---

## ToolContext

```python
@dataclass
class ToolContext:
    agent_id: str
    session_id: str
    allowed_paths: list[str]      # from permissions.workspace_paths in agent YAML
    allowed_commands: list[str]   # from permissions.allowed_commands in agent YAML
```

Use `allowed_paths` to enforce path restrictions (`file_tools.py` has a `_assert_path_allowed` helper you can reuse). Use `allowed_commands` to whitelist executables for `run_command`-style tools.

---

## Making the tool available to an agent

One step: list the tool in the flow YAML.

In any `llm` block that should have access to the tool, add it to `tools:`:

```yaml
  think:
    type: llm
    ...
    tools:
      - my_tool
      - search_memory
```

The tool schema (name, parameters, description) is automatically injected into that block's system prompt. The LLM sees it and can choose to call it.

Then add a `tool_call` block and a transition to reach it:

```yaml
  think:
    type: llm
    ...
    tools:
      - my_tool
    transitions:
      my_tool: my_tool_block
      done: END
      default: think

  my_tool_block:
    type: tool_call
    tool: my_tool
    transitions:
      default: think
```

---

## How tool calls work end-to-end

1. LLM block responds with YAML: `action: my_tool` and `action_input: {param_one: "...", param_two: 3}`
2. Runner transitions to the `tool_call` block named in `transitions.my_tool`
3. `ToolCallBlock` reads `shared["action_input"]`, calls `get_tool("my_tool", tool_context)`
4. The wrapper injects `context` and calls your function
5. Return value is appended to `shared["messages"]` as a tool result
6. Block returns `"default"`, transitioning back (usually to the `llm` block)

---

## Tool design patterns

### Read-only information tool
Returns a string. No side effects. Example: `search_memory`, `read_file`, `list_files`.

```python
@tool
def get_weather(city: str, context: ToolContext) -> str:
    """Return current weather for a city. Data is from an internal API."""
    # fetch and return
    return f"Weather in {city}: ..."
```

### Mutating tool with path guard
Use `_assert_path_allowed` from `file_tools` to enforce workspace restrictions.

```python
from tools.file_tools import _assert_path_allowed

@tool
def append_to_log(path: str, line: str, context: ToolContext) -> str:
    """Append a line to a log file inside the agent's workspace."""
    resolved = _assert_path_allowed(path, context)
    with resolved.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return f"Appended to {path}"
```

### Tool that calls an external service
Import boto3 or requests inside the function, not at module level, to avoid slowing startup for agents that don't use the tool.

```python
@tool
def fetch_stock_price(ticker: str, context: ToolContext) -> str:
    """Fetch the current stock price for a ticker symbol from an internal data feed."""
    import boto3
    # ... call service
    return f"{ticker}: $123.45"
```

### Tool with complex output
Convert structured data to clean markdown or YAML strings — the LLM reads the result as text.

```python
@tool
def list_open_tasks(context: ToolContext) -> str:
    """List all open tasks from the task tracker. Returns YAML."""
    import yaml
    tasks = _fetch_tasks()
    return yaml.dump({"tasks": tasks}, default_flow_style=False)
```

---

## Parameter descriptions

The auto-generated parameter descriptions are generic (`"Parameter 'param_one'"`). To give the LLM better guidance, add richer descriptions by customising the schema in `tools/__init__.py`'s `_make_bedrock_tool` function — or simply put the parameter semantics in the docstring.

The most effective approach is a clear docstring that describes what each parameter means:

```python
@tool
def schedule_report(agent_id: str, cron_expr: str, topic: str, context: ToolContext) -> str:
    """
    Schedule a recurring report.
    agent_id: which agent generates the report (e.g. 'researcher').
    cron_expr: standard 5-field cron expression (e.g. '0 9 * * 1' for Monday 9am).
    topic: subject matter for the report prompt.
    """
```

---

## Existing tools reference

| Tool | Module | What it does |
|---|---|---|
| `read_file` | `file_tools` | Read a text file (UTF-8 + latin-1 fallback) |
| `write_file` | `file_tools` | Write/overwrite a file, creates parent dirs |
| `list_files` | `file_tools` | Recursive directory listing |
| `delete_file` | `file_tools` | Delete a file |
| `file_exists` | `file_tools` | Returns "true" / "false" |
| `store_memory` | `memory_tools` | Store text in ChromaDB with topic+realm |
| `search_memory` | `memory_tools` | Semantic search across all memory |
| `update_memory` | `memory_tools` | Update a memory entry by ID |
| `delete_memory` | `memory_tools` | Delete a memory entry by ID |
| `spawn_agent` | `agent_tools` | Run a sub-agent synchronously, return its output |
| `send_message` | `agent_tools` | Send async message to another agent's mailbox |
| `check_inbox` | `message_tools` | Read this agent's pending mailbox messages |
| `mark_message_processed` | `message_tools` | Move a message to processed |
| `run_command` | `command_tools` | Run a shell command (allowlisted executables only) |
| `schedule_agent` | `schedule_tools` | Create a scheduled/recurring agent run |
| `cancel_schedule` | `schedule_tools` | Remove a schedule |
| `list_schedules` | `schedule_tools` | Show all defined schedules |

---

## Testing a new tool

Write a small standalone test script. The `@tool` decorator is transparent — you can call the function directly with a fake `ToolContext`:

```python
from tools import ToolContext
from tools.my_new_module import my_tool

ctx = ToolContext(
    agent_id="test",
    session_id="test-session",
    allowed_paths=["workspace/test/"],
    allowed_commands=[],
)

result = my_tool(param_one="hello", param_two=42, context=ctx)
print(result)
```

Then run an agent that uses it and check `logs/<agent>/<session>.jsonl` for the `tool_call` event.
