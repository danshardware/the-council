# B2 — Create .env.template

## Overview

`getting-started.md` references `.env.template` but the file does not exist.
Create a minimal template that covers the required and optional environment
variables for a fresh Council deployment.

The only hard requirement is that boto3 can find AWS credentials.  The most
common patterns are:
- Mount the host `~/.aws` directory and set `AWS_PROFILE` + `AWS_DEFAULT_REGION`
- Provide `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` + `AWS_DEFAULT_REGION`
  directly (less preferred — credentials in env)

---

## File to Create

`.env.template` at the repo root.

---

## Content Spec

```dotenv
# ──────────────────────────────────────────────────────────────────
# Council — Environment Template
# Copy to .env and fill in your values.
# ──────────────────────────────────────────────────────────────────

# Unique name for this deployment — used to namespace Docker containers.
# No spaces. Example: council-acme or council-dev
COMPOSE_PROJECT_NAME=council-mycompany


# ── AWS Credentials ───────────────────────────────────────────────
# Option A (recommended): Mount your ~/.aws directory in compose.yaml
#   volumes:
#     - ~/.aws:/root/.aws:ro
# Then set only the region and profile name here:
AWS_DEFAULT_REGION=us-east-1
# AWS_PROFILE=default          # uncomment if using named profile

# Option B: Supply credentials directly (not recommended for shared machines)
# AWS_ACCESS_KEY_ID=AKIA...
# AWS_SECRET_ACCESS_KEY=...
# AWS_DEFAULT_REGION=us-east-1


# ── Discord (optional — configure after initial setup via Concierge) ──
# Do NOT add this before running onboarding.  The Concierge will walk
# you through the Discord configuration and tell you when to set this.
# DISCORD_BOT_TOKEN=


# ── Data directory override (optional) ───────────────────────────
# By default, Council stores all instance data in ./data/ relative to
# the compose file.  Override here if you want a different path.
# COUNCIL_DATA_DIR=/absolute/path/to/data
```

---

## Testing Plan

No automated test needed.  Manual checklist:

- [ ] `docker compose --env-file .env config` runs without error when `.env` is
      populated from the template
- [ ] A session can be started with only `COMPOSE_PROJECT_NAME` and AWS credentials set
- [ ] The template contains no real credentials

---

## Acceptance Criteria

- [ ] `.env.template` exists at the repo root
- [ ] File contains `COMPOSE_PROJECT_NAME`, both AWS auth options, `DISCORD_BOT_TOKEN`
      (commented), and data dir override (commented)
- [ ] Comments are clear enough for a non-technical deployer
- [ ] No real credentials or tokens in the template
- [ ] `getting-started.md` reference to `.env.template` is now valid

---

## QA Notes

- Add `.env` (without `.template`) to `.gitignore` if not already there.
- Do not add `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` as uncommented defaults —
  even with placeholder values, some scanners flag them.

---

## Instructions to the Coder

1. Create `.env.template` at the repo root with the content above.
2. Check `.gitignore` — add `.env` if absent.
3. Verify `getting-started.md`'s `cp .env.template .env` step now works.
