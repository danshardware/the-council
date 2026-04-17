# Production Validation Checklist

Run these checks after deploying the container for the first time, or after
any change to the Dockerfile / compose.yaml.

## 1. Pre-flight

- [ ] `.env` created from `.env.template` with real values
- [ ] `data/config/discord.yaml` present (copy from `config/discord.yaml` and fill in channel/guild IDs)
- [ ] `data/config/schedules.yaml` present (copy from `config/schedules.yaml.template` and customise)

## 2. Build + start

```bash
podman-compose build
podman-compose up -d
podman-compose logs -f council
```

Expected: startup banner printed, "Council Scheduler Daemon" rule visible, no Python traceback.

## 3. Discord connectivity

- [ ] Bot appears **Online** in the Discord server member list within ~10 s of startup
- [ ] Send `@BotName ping` (or any message in a mapped channel) — bot should acknowledge

## 4. Agent interaction via Discord

- [ ] Send a task to the CEO agent via Discord (e.g. "Summarise the latest campaign digest")
- [ ] Response appears in the Discord channel within a reasonable time
- [ ] Session log written to `data/logs/ceo/<session_id>.jsonl`

## 5. Memory write + retrieval

```bash
# Inside a running session, or via CLI:
podman-compose exec council uv run run.py \
  --agent ceo \
  --prompt "Remember this test fact: the sky is blue" \
  --local

# Then verify retrieval:
podman-compose exec council uv run memory.py search "sky colour"
```

- [ ] Fact stored without error
- [ ] Search returns the stored fact

## 6. State persistence across restart

```bash
podman-compose restart council
# Repeat step 5 retrieval — memory should still be present
```

- [ ] Memory survives container restart (ChromaDB data in `data/memory_db/`)
