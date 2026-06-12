# Setup Guide

Complete walkthrough from clone to a living dashboard. Expect **15–30 minutes** end to end,
most of it dependency installs. The short version is in the [README](../README.md#quick-start);
this guide adds detail, expected output, and the post-install configuration steps.

## 1. Prerequisites

| Tool | Why | Check |
|---|---|---|
| Docker Desktop | PostgreSQL 16 + Redis containers | `docker info` |
| uv | Python 3.12 + dependency management (no manual venvs) | `uv --version` |
| Node 18+ | React frontend dev server | `node --version` |
| git | clone + updates | `git --version` |

- **macOS / Linux**: everything works as-is.
- **Windows**: use **WSL2** (recommended — install everything inside the Linux environment),
  or Git Bash if you must stay native. `setup.sh` / `start.sh` are bash scripts and will not
  run in PowerShell. Native-Windows Python also needs a prebuilt `bcrypt` wheel — use 64-bit
  Python 3.12 and a current uv so you never compile it.

Install uv if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 2. Clone and configure

```bash
git clone <this-repo> firemaster && cd firemaster
./scripts/setup.sh
```

`setup.sh` creates `backend/.env` from `.env.example`, generates a random JWT secret, and
asks you to choose an **admin password** (stored as a bcrypt hash — the plaintext is never
written anywhere). Username is `admin`.

Re-running `setup.sh` later **overwrites `.env`** (it warns first). To change just the
password afterwards:

```bash
cd backend && uv run python -c "from app.core.auth import hash_password; print(hash_password('NEW-PASSWORD'))"
# paste the output into AUTH_PASSWORD_HASH in backend/.env, then restart the stack
```

## 3. Start the stack

```bash
./scripts/start.sh
```

This single script:

1. clears anything stale on ports 8000/5173,
2. starts **postgres** and **redis** via Docker Compose (first run pulls images),
3. applies database migrations (`alembic upgrade head` — on a fresh database this builds the
   full schema),
4. starts the **backend** (FastAPI on :8000), the **Celery worker** (background sync jobs),
   and the **frontend** (Vite on :5173).

First run also installs Python deps (`uv sync` happens implicitly via `uv run`) and you should
run `npm install` in `frontend/` if the frontend fails to start. Leave this terminal running;
`Ctrl+C` stops all services.

Sanity checks: `http://localhost:8000/api/health` returns ok, `http://localhost:5173` shows
the login screen.

## 4. Seed data — demo first

A fresh database renders empty pages. Seed the **demo persona** to see the app working at
full depth before you connect anything real:

```bash
cd backend
uv run python ../scripts/seed_demo.py
uv run python ../scripts/seed_scenarios.py   # optional: example what-if scenarios
```

The demo persona is a 52-year-old just past a layoff: severance and unemployment running out,
three properties (a mortgaged primary, a secondary home under contract to sell, a rented-out
income property), a 401(k)/IRA stack, startup equity, ~2 years of net-worth history, and a
SEPP/72(t) bridge plan to 59½. The Retirement page shows the whole story — including the cash
pool brushing zero at ~57 before the planned downsize rescues it. That's the point: this is
what catching a bridge problem *years in advance* looks like.

Demo mechanics worth knowing:

- **Safe**: it refuses to run against a database that already has Monarch-synced data.
- **Idempotent**: re-running re-anchors all dates to today and updates in place.
- **Removable**: `uv run python ../scripts/seed_demo.py --remove` deletes every demo row.
  Demo rows are manual-source, so they coexist safely with a later real Monarch sync until
  you do.

If you'd rather start blank (no demo), seed just a starter FIRE config so the Retirement page
has something to project: `uv run python ../scripts/seed_config.py`.

## 5. Log in and tour

Open **http://localhost:5173**, log in (`admin` / your password). Suggested order with demo
data: **Dashboard** (net worth + history) → **Retirement** (the projection — hover the event
markers) → **Runway** (cash months remaining) → the **Config** page (every assumption driving
what you just saw).

## 6. Go live: connect Monarch

When you're ready for your real data, follow [MONARCH_SETUP.md](MONARCH_SETUP.md):
authenticate once, hit **Sync Now**, enrich your accounts with FIRE roles, then remove the
demo rows. Property owners: also see the property import section there and
[PROPERTY_MODULE.md](PROPERTY_MODULE.md).

## 7. Make the config yours

Everything the projections assume lives in one place: the **Config** page (base plan) plus
**scenarios** (named override sets compared on the Retirement page).

- Base config: date of birth, target spending, Social Security, healthcare, withdrawal
  strategy, and the `custom_assumptions` blocks (SEPP plan, property sales, tax profile,
  projection rates — all rates are **real**, after inflation).
- Scenarios store only their *differences* from the base, so editing the base updates every
  scenario that doesn't override that field.
- Property sales are modeled with `property_sales` entries (any sale month, dynamic value,
  capital gains incl. §121, mortgage payoff via amortization, proceeds to a taxable pool).
  The seeded examples in `scripts/seed_scenarios.py` show the full key set.

## 8. Staying up to date

```bash
git pull
cd backend && uv sync && uv run alembic upgrade head
cd ../frontend && npm install
./scripts/start.sh
```

Migrations are always safe to re-run. After pulling engine changes, note the Celery worker
needs the restart (`start.sh` handles it).

## 9. Troubleshooting

Start with the [README's troubleshooting table](../README.md#troubleshooting). Additional
detail:

- **Login fails with correct password** — `AUTH_PASSWORD_HASH` in `backend/.env` must be a
  bcrypt hash (starts with `$2b$`). Regenerate via the one-liner in step 2. Settings are
  cached per-process: restart after editing `.env`.
- **Frontend can't reach the backend** — the frontend targets `http://localhost:8000` by
  default; override with `VITE_API_URL` (see `frontend/.env.example`) if you moved the API.
- **Migrations fail on an existing database** — you likely have a database from an older
  install. For a clean slate: `docker compose down -v` (DESTROYS local data) and re-run
  `start.sh`.
- **Celery logs show no tasks registered** — the worker must run with
  `-I app.tasks.sync_tasks` (start.sh does this).
