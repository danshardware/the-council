# T07: Daemon Auto-Start and `--local` Flag

## File modified
`run.py`

## Design

There is **no `--mode discord` flag**. Discord (and any future channels) start automatically
whenever credentials and config are available. The `--local` flag explicitly suppresses this.

```
uv run run.py --daemon                # starts scheduler + Discord if available
uv run run.py --daemon --local        # starts scheduler only (no channels)
uv run run.py --agent ceo --prompt .. # single-shot agent run (no channels)
```

## `--local` flag

```python
parser.add_argument(
    "--local",
    action="store_true",
    help="Local-only mode: suppress all channel gateways even if credentials are available."
)
```

## `_start_channel_gateways()` (called in daemon mode unless `--local`)

```python
def _start_channel_gateways() -> None:
    _start_discord_gateway()
    # Future: _start_slack_gateway(), _start_teams_gateway()
```

## `_start_discord_gateway(config_path="config/discord.yaml")`

1. Check `DISCORD_BOT_TOKEN` in env — if absent, return silently.
2. Check `config/discord.yaml` exists — if absent, log a yellow warning and return.
3. Load config, build `discord.Client` via `build_discord_client()`.
4. Start `client.run(token)` in a **daemon background thread** named `discord-gateway`.
   (Discord's event loop lives entirely in that thread; scheduler runs on the main thread.)

## Startup log

```
[Discord] Starting gateway in background thread…
[Discord] Connected as CouncilBot#1234 — listening on 1 guild(s)
```

> `run.py` already calls `load_dotenv()` at the top, so a `.env` file at the project root
> is the recommended approach for local dev.
> Never commit `.env` to version control.

## Acceptance Criteria

- [ ] **AC-01**: `uv run run.py --daemon` starts Discord gateway when token + config present.
- [ ] **AC-02**: `uv run run.py --daemon --local` skips Discord entirely.
- [ ] **AC-03**: Missing token — no error, no gateway, scheduler still starts.
- [ ] **AC-04**: Missing config but token present — yellow warning logged, scheduler still starts.
- [ ] **AC-05**: Background scheduler starts in all cases (Discord never blocks it).

## Progress

- [x] `--local` argument added
- [x] `_start_channel_gateways()` implemented
- [x] `_start_discord_gateway()` implemented
- [x] Discord runs in daemon thread alongside BlockingScheduler
- [ ] Tests pass (see T08)
- [ ] Complete
