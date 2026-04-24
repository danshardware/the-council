# Discord Configuration Guide

This guide is for the Ops agent (and human operators) configuring the Discord gateway.

---

## How Discord routing works

1. A message arrives in a Discord channel.
2. The gateway looks up the channel's ID in `data/config/discord.yaml`.
3. If the channel has an explicit mapping → the message is routed to that agent.
4. If the channel has no mapping AND `routing_fallback_llm: true` → Nova Lite reads the available agents' descriptions and picks the best fit.
5. If neither applies → the bot posts a clarification message and does nothing.

---

## Config file location

The runtime reads **`data/config/discord.yaml`** (inside the mounted data volume).
The file at `config/discord.yaml.template` in the repo is a reference only — it is never loaded.

---

## Full file format

```yaml
# IANA timezone for business-hours retry window (human-input retries).
timezone: America/New_York

guilds:
  - guild_id: "1234567890123456789"   # Discord server ID (string)
    name: "My Company"                 # Human label — not used by routing
    channels:
      - channel_id: "9876543210987654321"  # Discord channel ID (string)
        name: "general"                    # Human label — not used by routing
        agent: ceo                         # Must match an agent ID in agents/
      - channel_id: "1111111111111111111"
        name: "ops-chat"
        agent: ops
    # true  → unmapped channels go to LLM routing
    # false → unmapped channels get a clarification message from the bot
    routing_fallback_llm: true

  # Multiple guilds are supported
  - guild_id: "9999999999999999999"
    name: "Partner Server"
    channels:
      - channel_id: "2222222222222222222"
        name: "council-requests"
        agent: researcher
    routing_fallback_llm: false
```

### Field reference

| Field | Type | Required | Notes |
|---|---|---|---|
| `timezone` | string | Yes | IANA name, e.g. `America/New_York`, `Europe/London`, `UTC` |
| `guilds` | list | Yes | At least one entry required |
| `guilds[].guild_id` | string | Yes | Right-click server → Copy Server ID (requires Developer Mode) |
| `guilds[].name` | string | No | Label only; not used by routing |
| `guilds[].channels` | list | No | Omit to rely entirely on LLM fallback |
| `guilds[].channels[].channel_id` | string | Yes | Right-click channel → Copy Channel ID |
| `guilds[].channels[].name` | string | No | Label only; not used by routing |
| `guilds[].channels[].agent` | string | Yes | Must match an `id:` field in `agents/*.yaml` |
| `guilds[].routing_fallback_llm` | bool | No | Default: `false` |

---

## Getting IDs from Discord

Enable Developer Mode first: **User Settings → Advanced → Developer Mode → ON**

| ID needed | How to get it |
|---|---|
| Guild ID | Right-click the server name in the left sidebar → **Copy Server ID** |
| Channel ID | Right-click the channel name → **Copy Channel ID** |

IDs are always numeric strings. Store them in quotes in the YAML.

---

## Common tasks

### Add a new channel mapping

Ask the Ops agent:

```
Add Discord channel mapping: channel_id=1234567890123456789, channel_name=research-requests, agent=researcher
```

Or edit `data/config/discord.yaml` directly and add an entry under the correct guild's `channels` list:

```yaml
      - channel_id: "1234567890123456789"
        name: "research-requests"
        agent: researcher
```

Restart the container (or send `SIGHUP` to the gateway thread) for the change to take effect.

---

### Remove a channel mapping

Ask the Ops agent:

```
Remove the Discord channel mapping for channel_id=1234567890123456789
```

Or delete the corresponding entry from `data/config/discord.yaml`.

---

### Change which agent handles a channel

Ask the Ops agent:

```
Update Discord channel 1234567890123456789 to use the ops agent instead of ceo
```

Or update the `agent:` field for that channel entry in `data/config/discord.yaml`.

---

### Add a second Discord server (guild)

Add a second entry to the `guilds` list:

```yaml
  - guild_id: "9999999999999999999"
    name: "Second Server"
    channels:
      - channel_id: "5555555555555555555"
        name: "general"
        agent: concierge
    routing_fallback_llm: true
```

One bot token can be in multiple servers simultaneously — no extra tokens needed.

---

### Enable or disable LLM fallback routing

Set `routing_fallback_llm` for the guild:

```yaml
    routing_fallback_llm: true   # unmapped channels use Nova Lite to pick an agent
    routing_fallback_llm: false  # unmapped channels get a "I don't know which agent" reply
```

When `true`, Nova Lite picks from all agents that have `discord.enabled: true` in their agent YAML.

---

### Exclude an agent from LLM fallback routing

Set `discord.enabled: false` in the agent's YAML. This prevents the agent from appearing
in the LLM routing pool even if `routing_fallback_llm: true` for the guild.

Note: explicit `channel_id` mappings always work regardless of this flag.

```yaml
# In agents/ops.yaml (example)
discord:
  enabled: false   # ops won't be selected by LLM fallback; only via explicit channel mapping
```

---

## Agent-level Discord display settings

Each agent YAML can have a `discord:` block that controls how its replies appear in Discord threads:

```yaml
discord:
  enabled: true          # Include this agent in LLM fallback routing (default: true)
  embed_name: "Ralph (CEO)"   # Display name shown in the embed header
  embed_color: 0x1a237e       # Embed sidebar colour as a hex integer
  emoji: "🎩"            # Emoji added to the channel while the agent is thinking
```

These are optional. If omitted, the bot uses the agent's `name:` field and a default colour.

---

## Applying changes

Changes to `data/config/discord.yaml` are NOT hot-reloaded. After editing the file:

```bash
# Restart the container
docker compose restart council

# Or with Podman
podman compose restart council
```

Verify the gateway started:

```bash
docker compose logs council | grep -i discord
# Expected: [Discord] Starting gateway in background thread…
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Gateway does not start | `DISCORD_BOT_TOKEN` missing or `data/config/discord.yaml` missing | Add token to `.env`; create config file |
| Bot online but not responding | Channel ID not mapped and fallback disabled | Add explicit channel mapping or enable `routing_fallback_llm` |
| Bot responds to wrong agent | `channel_id` mismatch (name-only config) | Verify the numeric channel ID — do not rely on channel names |
| LLM fallback picks wrong agent | Agent descriptions are too similar or vague | Add explicit channel mapping, or set `discord.enabled: false` on unwanted agents |
| Bot responds in the wrong timezone (retry window) | `timezone` set incorrectly | Update `timezone` in `data/config/discord.yaml` to the correct IANA name |
