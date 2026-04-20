# The Council

A local multi-agent system. Multiple AI agents (backed by AWS Bedrock) run concurrently, communicate via an async file-based mailbox, share a ChromaDB memory store, and can spawn sub-agents or schedule future work.

---

## Quick start

```bash
# Install dependencies
uv sync

# Copy and fill in environment variables
cp .env.template .env

# Run a single agent
uv run run.py --agent ceo --prompt "Draft a strategy for entering the Nigerian market"

# Start the daemon (mailbox poller + scheduled jobs + Discord gateway)
uv run run.py --daemon

# Start the daemon without channel gateways (local dev mode)
uv run run.py --daemon --local
```

---

## Stack

| Concern | Choice |
| --- | --- |
| Python | 3.12, managed by `uv` |
| LLM API | AWS Bedrock via `boto3` |
| Agent framework | PocketFlow (vendored at `pocketflow/`) |
| Vector memory | ChromaDB + Bedrock Titan Embeddings v2 |
| Scheduling | APScheduler |
| CLI display | Rich |
| Agent / flow config | YAML |

---

## Directory map

```
agents/           YAML definitions for each agent
config/           Config files (discord.yaml, guardrails.yaml, schedules.yaml.template, …)
conversation/     Bedrock conversation API wrapper
data/             Mutable runtime state — mounted as a volume in production (see below)
engine/           Core runtime: runner, scheduler, mailbox, logger, blocks, flow loader
flows/            YAML flow definitions
memory/           ChromaDB store + import pipeline
pocketflow/       Vendored PocketFlow framework
tools/            Tool registry + all built-in tools
tests/            pytest suite + production validation checklist
docs/             Onboarding guide, how-to docs
```

---

## Running in a container

### Build

```bash
podman build -t council:latest .
```

### Single instance

```bash
# Start
podman-compose up -d

# Logs
podman-compose logs -f council

# Stop
podman-compose down
```

`compose.yaml` mounts `./data` into the container and reads credentials from `.env`.
`data/` is created and initialised automatically on first start.

### Configuration

All mutable state lives under `data/` and is never baked into the image:

```
data/
├── agents/          # override built-in agent YAMLs (optional)
├── flows/           # override built-in flow YAMLs (optional)
├── config/
│   ├── discord.yaml         # required for Discord gateway
│   └── schedules.yaml       # runtime schedules (copy from config/schedules.yaml.template)
├── shared_knowledge/        # company context files injected into agent prompts
├── logs/            # JSONL session traces (auto-created)
├── memory_db/       # ChromaDB persistence (auto-created)
├── messages/        # agent mailboxes (auto-created)
└── workspace/       # per-agent scratch space (auto-created)
```

Any file placed in `data/agents/`, `data/flows/`, or `data/config/` shadows the built-in
copy from the image. Files not present fall through to the built-in defaults.

---

## Multi-instance deployment

To run multiple independent instances — each with its own agents, Discord server, and data — share one built image and give each instance its own directory.

### Instance directory layout

```
/deployments/
├── instance-acme/
│   ├── compose.yaml       ← copy of instance.compose.yaml.template
│   ├── .env               ← unique COMPOSE_PROJECT_NAME + credentials
│   └── data/
│       ├── agents/        ← instance-specific agent overrides
│       ├── config/
│       │   ├── discord.yaml      ← this instance's guild + channel mapping
│       │   └── schedules.yaml
│       └── shared_knowledge/     ← this instance's company context
│
└── instance-personal/
    ├── compose.yaml
    ├── .env
    └── data/
        └── …
```

### Steps

1. **Build the image once** from the repo:
   ```bash
   podman build -t council:latest /path/to/council-repo
   ```

2. **Create an instance directory** and copy the template compose file:
   ```bash
   mkdir -p /deployments/instance-acme
   cp /path/to/council-repo/instance.compose.yaml.template /deployments/instance-acme/compose.yaml
   cp /path/to/council-repo/.env.template /deployments/instance-acme/.env
   ```

3. **Edit `.env`** — the critical field is `COMPOSE_PROJECT_NAME`, which namespaces all
   container names so instances don't collide:
   ```dotenv
   COMPOSE_PROJECT_NAME=council-acme
   AWS_ACCESS_KEY_ID=…
   AWS_SECRET_ACCESS_KEY=…
   AWS_DEFAULT_REGION=us-east-1
   DISCORD_BOT_TOKEN=…
   ```

4. **Populate `data/`** with the instance-specific overrides (discord.yaml, agent YAMLs,
   shared_knowledge, etc.).

5. **Start the instance**:
   ```bash
   cd /deployments/instance-acme
   podman-compose up -d
   ```

Each instance runs in a fully isolated container with its own data volume.
Rebuilding the image automatically applies to all instances on their next restart.

---

## Memory CLI

```bash
uv run memory.py list --realm knowledge_base
uv run memory.py search "product strategy"
uv run memory.py import data/shared_knowledge/company/ --topic "company overview" --realm institutional
```

---

## Tests

```bash
# Run the full suite (excludes tests requiring live AWS / browser)
uv run pytest tests/ --ignore=tests/test_browse_web_tool.py --ignore=tests/test_external_services.py

# Container smoke test (requires podman)
uv run pytest tests/test_container.py -v -s
```

See [tests/PRODUCTION_CHECKLIST.md](tests/PRODUCTION_CHECKLIST.md) for the manual validation
steps to run after deploying a new instance.

---

## Further reading

- [docs/project-onboarding.md](docs/project-onboarding.md) — full architecture walkthrough
- [docs/how-to-add-tools.md](docs/how-to-add-tools.md) — adding tools to the registry
- [docs/how-to-create-agents.md](docs/how-to-create-agents.md) — defining a new agent
- [CONSTITUTION.md](CONSTITUTION.md) — guiding principles
