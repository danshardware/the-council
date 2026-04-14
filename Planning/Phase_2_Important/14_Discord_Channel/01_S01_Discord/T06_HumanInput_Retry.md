# T06: HumanInputBlock Extension + Retry Scheduler

## Files modified
- `engine/block.py` — `HumanInputBlock` (extend existing class)
- `engine/scheduler.py` — new `_schedule_discord_retry()` helper

---

## Current `HumanInputBlock` behaviour (local — no channel)

Prints to stdout, reads from stdin. When `channel_context` is absent, behaviour
**does not change** — stdin path preserved exactly as-is.

---

## New behaviour when `channel_context` is present

### Phase 1 — Ask (sync, runs inside `HumanInputBlock.exec`)

```python
def _ask_via_channel(self, shared: dict, question: str) -> None:
    adapter: ChannelAdapter = shared["_channel_adapter"]
    ctx: dict = shared["channel_context"]
    loop = shared["_discord_loop"]

    # 1. If no thread yet, create one now
    if ctx["thread_id"] is None:
        thread_id = asyncio.run_coroutine_threadsafe(
            adapter.create_thread(ctx, ctx["message_id"], name="Agent question"),
            loop,
        ).result(timeout=10)
        ctx["thread_id"] = thread_id

    # 2. Post question embed in thread
    asyncio.run_coroutine_threadsafe(
        adapter.send_embed(ctx, title="Question", description=question, in_thread=True),
        loop,
    ).result(timeout=10)

    # 3. Save checkpoint & raise SuspendExecution
    checkpoint_path = _save_checkpoint(shared)
    ctx["pending_checkpoint"] = checkpoint_path
    ctx["retry_count"] = 0
    raise SuspendExecution(checkpoint_path)
```

`_save_checkpoint` is the existing logic in `CheckpointBlock` — extract it into a
module-level helper so both `CheckpointBlock` and `HumanInputBlock` can use it.

---

## Phase 2 — Retry scheduler

After `SuspendExecution` is raised and caught by the gateway, the gateway calls:

```python
schedule_discord_retry(channel_context=ctx, agent_id=..., session_id=...)
```

This registers an APScheduler job (using the background scheduler already running):

```python
def schedule_discord_retry(
    channel_context: dict,
    agent_id: str,
    session_id: str,
    scheduler,           # the BackgroundScheduler instance
    timezone: str,       # from config/discord.yaml
) -> str:
    """Register a retry ping job. Returns job_id."""
    job_id = f"discord_retry_{session_id}"
    scheduler.add_job(
        _discord_retry_job,
        trigger=CronTrigger(
            hour="9-17",          # 09:00–17:00 every hour
            minute=0,
            timezone=timezone,
        ),
        args=[channel_context, agent_id, session_id, scheduler],
        id=job_id,
        replace_existing=True,
        max_instances=1,
    )
    return job_id
```

### `_discord_retry_job` logic

```
1. Increment ctx["retry_count"]

2. If retry_count <= 3:
     ping the human via adapter.ping_human(ctx, attempt=retry_count)
     → @author_id in thread: "Still waiting for your input (attempt N/3).
       If you don't reply, I'll continue without you."

3. If retry_count > 3:
     remove this job from scheduler
     resume checkpoint with system injection:
       "[SYSTEM] Human has not responded after 3 attempts. Continuing without their input."
     clear pending_checkpoint from ctx
```

Ping timing = "every hour between 09:00–17:00 in configured timezone".
With a 4-hour effective gap: the job fires every hour but only 3 total pings are allowed
before giving up. Each hour between 09:00–17:00 counts as one potential ping slot;
the job stops after 3 (not 3 × 8-hour windows — just 3 total pings, whenever they fall
inside business hours).

---

## `shared_overrides` in `runner.py`

One-line change: in `AgentRunner.run()`, after `shared = {...}` is built, merge overrides:

```python
if shared_overrides:
    shared.update(shared_overrides)
```

Add `shared_overrides: dict | None = None` to the `run()` signature.

---

## Acceptance Criteria

- [ ] **AC-01**: When no `channel_context` in shared, `HumanInputBlock` reads from stdin unchanged.
- [ ] **AC-02**: When `channel_context` present, question embed posted to Discord thread.
- [ ] **AC-03**: `SuspendExecution` raised after posting; checkpoint saved to disk.
- [ ] **AC-04**: Retry job registered; fires `ping_human` at most 3 times inside business hours.
- [ ] **AC-05**: After 3rd unanswered ping, agent resumes with `[SYSTEM]` injection (no stdin).
- [ ] **AC-06**: Human replies in thread → agent resumes correctly (via thread watcher in T04).
- [ ] **AC-07**: `runner.py` accepts `shared_overrides` and merges cleanly.

## Progress

- [ ] Task started
- [ ] `HumanInputBlock._ask_via_channel()` written
- [ ] `_save_checkpoint` extracted as shared helper
- [ ] `schedule_discord_retry` written in `scheduler.py`
- [ ] `_discord_retry_job` written and tested
- [ ] `runner.py` `shared_overrides` extension
- [ ] Tests pass (see T08)
- [ ] Complete
