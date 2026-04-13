# T08: Tests

## Test files

| File | Scope |
|---|---|
| `tests/test_discord_router.py` | Unit: routing logic, LLM fallback, opt-out |
| `tests/test_discord_gateway.py` | Integration: mock discord events → mailbox/runner |
| `tests/test_discord_adapter.py` | Unit: `DiscordAdapter` method calls and embed building |
| `tests/test_discord_retry.py` | Unit: retry scheduler — ping count, business hours, resume |
| `tests/test_channel_tools.py` | Unit: tool availability gating, no-adapter error |

---

## `tests/test_discord_router.py`

```python
# Fixtures: minimal config dict, minimal agent_configs dict

def test_channel_map_hit_no_llm_call():
    # channel_id in config → returns correct agent_id; assert no LLM call made

def test_channel_map_miss_llm_fallback():
    # channel not in config, routing_fallback_llm=True
    # mock call_llm to return "researcher"
    # assert result.agent_id == "researcher", result.method == "llm"

def test_channel_map_miss_llm_returns_unclear():
    # LLM returns "unclear" → result.unclear == True

def test_fallback_disabled_returns_unclear():
    # routing_fallback_llm=False, no channel match → result.unclear == True

def test_disabled_agent_excluded_from_llm_prompt():
    # agent with discord.enabled=false must not appear in the LLM routing prompt
    # mock call_llm, capture the prompt text, assert disabled agent not in it

def test_load_discord_config_missing_file():
    # raises FileNotFoundError with path in message

def test_token_env_not_read_by_router():
    # router never reads the token env var — it shouldn't even know about it
    # just check the router module has no os.environ access at all — token reading lives only in gateway
```

---

## `tests/test_discord_adapter.py`

```python
# Use unittest.mock to patch discord.py objects; no real Discord connection.

def test_add_reaction_called_with_correct_emoji():
def test_clear_reactions_calls_clear_on_message():
def test_send_embed_uses_agent_colour_and_name():
def test_create_thread_returns_thread_id():
def test_ping_human_mentions_author_id():
```

---

## `tests/test_discord_gateway.py`

Mock `discord.Client` and `discord.Message`. Test the event-handling logic in isolation.

```python
def test_bot_own_messages_ignored():
    # msg.author == client.user → on_message returns early, no routing

def test_routing_hit_triggers_agent_runner():
    # mock router returns agent_id="ceo"
    # assert AgentRunner.run called with correct agent_id and prompt

def test_routing_unclear_posts_clarification_not_thread():
    # router returns unclear → no thread created, clarification text sent to channel

def test_reaction_lifecycle_success():
    # router hit, runner succeeds → reactions: 👀 + emoji → cleared → ✅

def test_reaction_lifecycle_error():
    # runner raises → reactions cleared → ❌ → error message in thread

def test_thread_created_on_channel_message():
    # human message → thread created with correct name prefix
```

---

## `tests/test_discord_retry.py`

```python
def test_retry_job_pings_up_to_3_times():
    # call _discord_retry_job 4 times on a mock context
    # first 3 → ping called; 4th → resume called, job removed

def test_retry_job_removes_itself_after_3_pings():
    # after 3rd ping, scheduler.remove_job called

def test_retry_resume_injects_system_message():
    # on 4th call, agent resumed with "[SYSTEM] Human has not responded..."

def test_business_hours_trigger_config():
    # CronTrigger for retry job has hour="9-17" and correct timezone
```

---

## `tests/test_channel_tools.py`

```python
def test_send_channel_message_requires_adapter():
    # shared has no _channel_adapter → RuntimeError

def test_post_channel_embed_proactive_no_context():
    # no channel_context but channel_id provided explicitly → posts to channel directly

def test_disabled_agent_raises_permission_error():
    # agent config discord.enabled=False → PermissionError when tool called
```

---

## Notes

- No real Discord connections in any test. All discord.py objects are `MagicMock`.
- No real Bedrock calls in any test. LLM calls mocked via `unittest.mock.patch`.
- Follow existing test convention: plain `pytest`, no fixtures framework, no AWS mocking.

## Acceptance Criteria

- [ ] **AC-01**: All tests in all 5 files pass with `uv run pytest tests/test_discord_*.py`.
- [ ] **AC-02**: No real network calls made during test run.
- [ ] **AC-03**: Test coverage includes all ACs from T02–T07.

## Progress

- [ ] Task started
- [ ] `test_discord_router.py` written and passing
- [ ] `test_discord_adapter.py` written and passing
- [ ] `test_discord_gateway.py` written and passing
- [ ] `test_discord_retry.py` written and passing
- [ ] `test_channel_tools.py` written and passing
- [ ] Complete
