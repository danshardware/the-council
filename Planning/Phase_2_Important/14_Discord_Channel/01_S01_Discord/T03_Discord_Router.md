# T03: Discord Router

## Files
- `engine/discord_router.py`
- `config/discord.yaml` (new)
- Agent YAML modifications: `agents/*.yaml` — add `discord:` block

---

## `config/discord.yaml` Schema

```yaml
# Council Discord configuration
#
# Bot token: NEVER put it here.
# Set DISCORD_BOT_TOKEN in your environment (or .env file).
# run.py calls load_dotenv() at startup, so a .env file at the project root works.

timezone: Europe/London                  # for business-hours retry window (IANA tz name)
poll_interval_seconds: 5                 # polling fallback (--mode discord --poll)

guilds:
  - guild_id: "123456789012345678"
    name: "Acme Corp"
    channels:
      # Explicit channel→agent mapping (highest priority)
      - channel_id: "111111111111111111"
        name: "ceo-chat"
        agent: ceo
      - channel_id: "222222222222222222"
        name: "research"
        agent: researcher
    # If true, messages in unmapped channels go to Nova Lite for routing.
    # If false, unmapped messages get the clarification prompt instead.
    routing_fallback_llm: true
```

Multiple `guilds` entries = multiple companies, each with their own channel map.
All guilds share the same bot token.

---

## Agent YAML `discord:` block

Add to each agent YAML under a top-level `discord:` key:

```yaml
discord:
  enabled: true           # default true; set false to hide from Discord entirely
  embed_name: "Ralph (CEO)"
  embed_color: 0x1a237e    # hex int, used for embed sidebar colour
  emoji: "🎩"             # reaction emoji added when this agent picks up a message
  icon_url: ""            # optional: URL to agent avatar image (env var expansion OK)
```

Agents with `enabled: false` are excluded from the router's candidate list and are
unavailable via the LLM fallback path.

---

## `engine/discord_router.py`

### Routing algorithm (in order, first match wins)

1. **Explicit channel map**: look up `channel_id` in `config/discord.yaml`→`guilds[*].channels`.
   If found, return the mapped `agent_id`.

2. **LLM fallback** (if `routing_fallback_llm: true` and no channel match):
   Call Nova Lite with a short prompt listing enabled Discord agents and the message text.
   Expected response: `agent_id` or the literal string `unclear`.

3. **Clarification** (no match, or LLM returned `unclear`, or fallback disabled):
   Return a special sentinel `ROUTE_UNCLEAR` — caller is responsible for posting the
   clarification message to the channel.

### Module interface

```python
class RouterResult:
    agent_id: str | None        # None when ROUTE_UNCLEAR
    unclear: bool
    method: Literal["map", "llm", "unclear"]

def load_discord_config(path: str = "config/discord.yaml") -> dict: ...

def route_message(
    guild_id: str,
    channel_id: str,
    message_content: str,
    config: dict,
    agent_configs: dict[str, dict],   # agent_id → loaded agent YAML
) -> RouterResult: ...
```

`route_message` is **synchronous** (Nova Lite call uses `call_llm` from `engine/llm.py`
with a minimal single-turn prompt, not a full Conversation — keep it cheap: Nova Lite,
not Claude).

### LLM routing prompt (kept in `engine/discord_router.py` as a module constant)

```
You are a routing assistant. Given a message from a user, pick the most appropriate agent.

Available agents:
{agent_list}

User message: "{message}"

Reply with ONLY the agent_id (e.g. "ceo") or the word "unclear" if you cannot decide.
```

### Acceptance Criteria

- [ ] **AC-01**: Channel in config → correct agent returned, no LLM call made.
- [ ] **AC-02**: Unknown channel with `routing_fallback_llm: true` → LLM called, returns agent.
- [ ] **AC-03**: LLM returns `unclear` or fallback disabled → `RouterResult.unclear == True`.
- [ ] **AC-04**: Agents with `discord.enabled: false` excluded from LLM candidate list.
- [ ] **AC-05**: `load_discord_config` raises `FileNotFoundError` with clear message if yaml missing.
- [ ] **AC-06**: Bot token (`DISCORD_BOT_TOKEN`) is never read or referenced in this module; only the gateway reads it.

## Progress

- [ ] Task started
- [ ] `config/discord.yaml` template written
- [ ] Agent YAML `discord:` block documented and added to existing agents
- [ ] `discord_router.py` implemented
- [ ] Tests pass (see T08)
- [ ] Complete
