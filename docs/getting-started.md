# Getting Started — Fresh Install Guide

This guide walks you through a brand-new Council deployment from zero to a working system. Follow these steps in order.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Docker / Podman + Compose | For containerised deployment |
| AWS account | With Bedrock model access enabled (Claude Sonnet/Opus + Titan Embeddings) |
| AWS credentials | IAM user or role with `bedrock:InvokeModel` permission |

---

## Step 1 — Create your instance directory

The Council image ships with no live configuration. All instance-specific settings live in a `data/` folder that you create and mount.

```bash
mkdir -p my-council/data
cd my-council
```

Copy the compose template from the repo (or use the one already in your directory):

```bash
# The compose.yaml should already exist if you got it from the installer
# It should reference the pre-built image, e.g.:
#   image: council:latest
```

---

## Step 2 — Set environment variables

Copy `.env.template` from the repo and fill it in:

```bash
cp /path/to/council-repo/.env.template .env
```

Minimum required variables:

```dotenv
# Unique name for this instance — used to namespace Docker containers
COMPOSE_PROJECT_NAME=council-mycompany

# AWS credentials for Bedrock
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
```

Discord is configured separately in Step 5 — do NOT add `DISCORD_BOT_TOKEN` yet.

---

## Step 3 — Start the system

```bash
docker compose up -d
docker compose logs -f council
```

You should see the scheduler daemon start. It will print a warning that Discord is not configured — this is expected.

---

## Step 4 — Talk to the system before Discord is set up

Before Discord (or any other channel) is configured, you communicate with agents directly via the **command line inside the container**.

```bash
# Open a shell in the running container
docker compose exec council bash

# Then run any agent:
uv run run.py --agent concierge --prompt "Hello, I'd like to set up the system"

# Or ask the ops agent to configure Discord:
uv run run.py --agent ops --prompt "Configure Discord: guild_id=123456789, channel_id=987654321, channel_name=general, agent=ceo"

# Or run an agent one-shot from outside the container:
docker compose exec council uv run run.py --agent ops --prompt "..."
```

You can also mount a local directory and run the CLI locally (without Docker) for initial setup:

```bash
# From the repo root (with uv installed):
uv run run.py --agent ops --prompt "Configure Discord: ..."
```

---

## Step 5 — Configure Discord

### 5a — Create a Discord bot

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications) → **New Application**
2. Under **Bot**: click **Add Bot** → copy the **Token**
3. Under **Bot → Privileged Gateway Intents**, enable:
   - **Message Content Intent**
4. Under **OAuth2 → URL Generator**: select scopes `bot`, permissions:
   - Read Messages / View Channels
   - Send Messages
   - Create Public Threads
   - Manage Messages
   - Add Reactions
   - Read Message History
5. Use the generated URL to invite the bot to your server

### 5b — Get your guild and channel IDs

In Discord: **User Settings → Advanced → Developer Mode** → ON

Then right-click your server name → **Copy Server ID** (guild_id)  
Right-click a channel → **Copy Channel ID** (channel_id)

### 5c — Add the bot token to `.env`

```dotenv
DISCORD_BOT_TOKEN=your-bot-token-here
```

### 5d — Have the Ops agent write the config file

Run the Ops agent to create `data/config/discord.yaml`:

```bash
docker compose exec council uv run run.py --agent ops --prompt \
  "Create the Discord config at data/config/discord.yaml with: timezone=America/New_York, guild_id=YOUR_GUILD_ID, guild_name=My Company, channel_id=YOUR_CHANNEL_ID, channel_name=general, agent=ceo, routing_fallback_llm=true"
```

You can also copy `config/discord.yaml.template` from the repo and fill in the values manually:

```bash
cp /path/to/council-repo/config/discord.yaml.template data/config/discord.yaml
# Edit data/config/discord.yaml — replace all "___" values with your real IDs
```

### 5e — Restart to activate Discord

```bash
docker compose restart council
docker compose logs -f council
```

You should now see `[Discord] Starting gateway in background thread…`

---

## Step 6 — Run onboarding

Once Discord is connected, invite the Concierge to get you set up:

In your configured Discord channel, send:
```
Hello — let's set up the system
```

Or via CLI:
```bash
docker compose exec council uv run run.py --agent concierge --prompt \
  "Hello, let's run the onboarding process for my organisation"
```

The Concierge will interview you and write `data/shared_knowledge/company/mission.md`, which all agents use as company context.

---

## Troubleshooting

### Discord gateway not starting
- Check that `DISCORD_BOT_TOKEN` is set in `.env`
- Check that `data/config/discord.yaml` exists and has real IDs (not `"___"`)
- Check logs: `docker compose logs council | grep -i discord`

### "No module named X" or import errors
- Rebuild the image: `docker build -t council:latest .`

### Agent produces no output / times out
- Verify AWS credentials: `docker compose exec council uv run -c "import boto3; boto3.client('bedrock-runtime', region_name='us-east-1').list_foundation_models()"`
- Check that your IAM role/user has `bedrock:InvokeModel` for the required model IDs

### Multiple instances sharing a Discord bot
Each instance must have its own bot application and token. A single bot token can only be connected to one running process at a time.

---

## Data directory reference

```
data/
├── config/
│   ├── discord.yaml         ← create from config/discord.yaml.template
│   └── schedules.yaml       ← create from config/schedules.yaml.template (optional)
├── agents/                  ← drop agent YAML overrides here (optional)
├── flows/                   ← drop flow YAML overrides here (optional)
├── shared_knowledge/        ← company context files (created by Concierge onboarding)
├── logs/                    ← session traces (auto-created)
├── memory_db/               ← ChromaDB (auto-created)
├── messages/                ← agent mailboxes (auto-created)
└── workspace/               ← per-agent scratch space (auto-created)
```

Any file in `data/agents/`, `data/flows/`, or `data/config/` **shadows** the built-in copy from the image. Files not present fall through to built-in defaults.
