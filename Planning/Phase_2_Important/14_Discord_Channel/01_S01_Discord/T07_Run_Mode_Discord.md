# T07: run.py `--mode discord`

## File modified
`run.py`

## New CLI flag

```
uv run run.py --mode discord
uv run run.py --mode discord --discord-config config/discord.yaml
```

`--mode discord` starts the Discord gateway process. Mutually exclusive with `--agent`
and `--daemon`.

## Implementation

```python
parser.add_argument(
    "--mode",
    choices=["discord"],
    default=None,
    help="Run mode. 'discord' starts the Discord gateway. "
         "Omit to run a single agent (use --agent) or the scheduler (use --daemon).",
)
parser.add_argument(
    "--discord-config",
    default="config/discord.yaml",
    help="Path to discord.yaml (default: config/discord.yaml)",
)
```

In `main()`, after argument parsing:

```python
if args.mode == "discord":
    from engine.discord_gateway import run_gateway
    run_gateway(config_path=args.discord_config)
    return
```

`run_gateway(config_path)`:
1. Loads `discord.yaml`.
2. Reads bot token from `os.environ["DISCORD_BOT_TOKEN"]`; raises `SystemExit(1)` with a clear message if not set (`load_dotenv()` is already called by `run.py` before this point, so a `.env` file at the project root works).
3. Builds the `BackgroundScheduler` (same as daemon mode) for retry jobs + scheduled tasks.
4. Creates `discord.Client` with `intents` = `discord.Intents.default()` + `message_content`.
5. Registers `on_ready` and `on_message` handlers.
6. Calls `client.run(token)` (blocking — takes over the process).

The background scheduler runs in its own thread (already supported via `BackgroundScheduler`).

## Startup log

```
[Discord] Token loaded from DISCORD_BOT_TOKEN ✓
[Discord] Config loaded: 1 guild(s), 3 channel mappings
[Discord] Connected as CouncilBot#1234
[Discord] Listening...
```

> Note: `run.py` already calls `load_dotenv()` at the top, so adding `DISCORD_BOT_TOKEN=...`
> to a `.env` file at the project root is the recommended local dev approach.
> Never commit `.env` to version control.

## Acceptance Criteria

- [ ] **AC-01**: `uv run run.py --mode discord` starts without error when token in env.
- [ ] **AC-02**: Missing token env var prints clear error and exits 1.
- [ ] **AC-03**: Missing `config/discord.yaml` prints clear error and exits 1.
- [ ] **AC-04**: `--mode discord` + `--agent` prints argument conflict error.
- [ ] **AC-05**: Background scheduler starts alongside gateway (scheduled tasks still fire).

## Progress

- [ ] Task started
- [ ] `--mode discord` argument added
- [ ] `run_gateway()` implemented in gateway module
- [ ] Error handling for missing token / config
- [ ] Tests pass (see T08)
- [ ] Complete
