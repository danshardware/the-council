# B5 — Getting Started Doc Update

## Overview

`docs/getting-started.md` describes a flow that doesn't match reality for two reasons:
1. References `.env.template` (now fixed by B2, but the doc step needs updating)
2. Implies daemon mode auto-starts onboarding — in practice the user must invoke the
   onboarding flow directly

This is a documentation-only change.

---

## Changes Required

### Step 2 — Environment variables

Update to reflect B2's `.env.template`:

```markdown
## Step 2 — Set environment variables

Copy `.env.template` and fill in the required values:

    cp .env.template .env

Minimum required:

    COMPOSE_PROJECT_NAME=council-mycompany
    AWS_DEFAULT_REGION=us-east-1

**Recommended**: mount your `~/.aws` directory (see `.env.template` comments)
instead of supplying raw keys. Discord is configured separately — do NOT add
`DISCORD_BOT_TOKEN` yet.
```

### Step 4 — First interaction (replace current wording)

The current Step 4 says "Talk to the system before Discord is set up" and describes
running any agent.  Replace with a clear onboarding instruction:

```markdown
## Step 4 — Run onboarding

The system does not auto-start.  Run the Concierge's onboarding flow directly:

    # From inside the container:
    docker compose exec council uv run run.py \
      --agent concierge --flow onboarding --prompt "begin onboarding"

    # Or locally (with uv and AWS credentials configured):
    uv run run.py --agent concierge --flow onboarding --prompt "begin onboarding"

The Concierge will interview you about your organisation, write the mission file,
optionally set up agents, and walk you through Discord configuration.

You can re-run this command at any time to update your setup.
```

### Remove or update the daemon note

The current text says "It will print a warning that Discord is not configured — this
is expected."  Keep this note but move it to after the onboarding step, not before.

---

## Acceptance Criteria

- [ ] Step 2 references `.env.template` correctly (file now exists per B2)
- [ ] Step 4 gives the exact command to run onboarding
- [ ] No instruction implies daemon mode will start onboarding automatically
- [ ] Onboarding re-run command is documented
- [ ] File reads coherently top to bottom

---

## Instructions to the Coder

1. Open `docs/getting-started.md`.
2. Apply the changes above.
3. Read the full file top to bottom to confirm it flows correctly.
