# Hosting the public demo — `demo.firemaster.io`

> **Status (2026-06-24):** plan agreed; platform decided. The scaffolding files this doc
> references (`docker-compose.demo.yml`, `frontend/Dockerfile.prod`, `Caddyfile`,
> `reset-demo.sh`) are **not built yet** — they're the next task. This doc is the playbook.

A single, public, **locked** demo instance — friends/family/interested-users can click around
the real app with the seeded demo persona, **without any real data or Monarch access**. It
makes the 1:1-onboarding funnel self-serve.

## What makes it safe + cheap

- **`DEMO_MODE=true`** (already built, on `main`): Monarch sync is hard-disabled — the session
  is never loaded, the Sync button is hidden, the app is locked to seeded demo data. This is
  the prerequisite for putting it on the public internet.
- **No real data ever** touches the box. The demo DB is the seeded persona only.
- **Auto-seed on first boot** + **nightly reset** keep it clean (one visitor's edits don't
  persist for the next).

## Platform decision

| Considered | Verdict |
|---|---|
| **DigitalOcean** ($6/mo droplet) | ✅ **Chosen.** USD billing, US company, runs our `docker compose` verbatim. |
| Hetzner (~€4/mo) | Cheapest, but **bills in euros** (German company) — ruled out on that. |
| Azure | ~$30+/mo for an always-on equivalent VM — too pricey for 24/7. (Azure *is* used for the one-off **Windows acceptance test** — see [AZURE_WINDOWS_TEST.md](AZURE_WINDOWS_TEST.md).) |
| Vercel | Can't host a stateful multi-container stack (Postgres/Redis/FastAPI) — static/serverless only. |
| Fly.io | Viable managed/scale-to-zero alternative; needs per-service adaptation (no docker-compose). Fallback if we tire of running a box. |

## Demo simplifications (vs. the full stack)

- **Drop Celery** (`celery-worker` + `celery-beat`): in `DEMO_MODE` there's no sync and nothing
  to schedule, so they're dead weight. Demo = **postgres + redis + backend + frontend**.
- **Production frontend**: serve a built static site via nginx, not the Vite dev server.
- **No `--reload`** on the backend.
- **Shared demo password**: set once at deploy via the interactive setup prompt (currently
  `YouGotThis2026` — no `$`, so no shell-quoting traps). Share it with demo users.

## Deploy playbook (~30 min)

1. **Provision** a $6 DigitalOcean droplet (Ubuntu), in a US region.
2. **DNS**: `demo.firemaster.io` → A record → the droplet's IP.
3. **Docker**: `ssh` in → `curl -fsSL https://get.docker.com | sh`.
4. **Clone + setup**: `git clone` (main) → `docker compose run --rm backend uv run python -m app.setup`, type the demo password at the prompt.
5. **Launch**: `DEMO_MODE=true docker compose -f docker-compose.yml -f docker-compose.demo.yml up -d`.
6. **HTTPS**: a small **Caddyfile** reverse-proxies `demo.firemaster.io` → frontend, `/api/*` → `backend:8000`; Caddy fetches + renews the TLS cert automatically.
7. **Nightly reset cron** (clean slate, ~10 s downtime at 4am ET):
   `0 9 * * * cd /srv/firemaster && docker compose -f … down -v && DEMO_MODE=true docker compose -f … up -d`

## Scaffolding to build (next task)

- `docker-compose.demo.yml` — overlay: drop Celery, bake `DEMO_MODE=true`, prod frontend, no `--reload`.
- `frontend/Dockerfile.prod` — 2-stage build → static site on nginx (calls are relative `/api`, so Caddy routes them).
- `Caddyfile` — `demo.firemaster.io` routing + auto-HTTPS.
- `reset-demo.sh` — the nightly wipe-and-reseed used by cron.

## Still open

- Pricing is from a Jan-2026 knowledge cutoff — sanity-check current DO rates (the *shape*
  holds: ~$6/mo).
- Multi-arch prebuilt images (see "Still open" in [CONTAINER_RUNBOOK.md](CONTAINER_RUNBOOK.md))
  would remove the first-build wait on the droplet — nice-to-have, not required.
