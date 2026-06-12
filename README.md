# FIREMaster

A self-hosted FIRE planning cockpit. Your real accounts, your real spending, your real
retirement math — running on your own machine, with an AI analyst that can read all of it.

FIREMaster answers the questions generic retirement calculators can't:

- *I just left my job at 52. Does the bridge to 59½ actually hold?*
- *What happens if I sell the rental in 18 months instead of carrying it?*
- *Where does cash run out — and which lever (spending, a property sale, a 72(t) plan) fixes it?*
- *What did this property really cost me last year, all-in?*

It does this with month-by-month wealth-pool projections (cash, taxable, IRAs, real estate,
private equity — each with its own rules), scenario comparison, SEPP/72(t) bridge modeling,
per-property P&L, and a spending tracker — all driven by data that syncs automatically from
your real accounts.

> **Not financial advice.** FIREMaster is a modeling tool you run yourself. Sanity-check the
> assumptions, and make decisions with a professional where it matters.

## The two-interface architecture

FIREMaster is deliberately built as two layers (see [ARCHITECTURE.md](ARCHITECTURE.md)):

1. **The cockpit** — a React dashboard for entering your plan and seeing state at a glance:
   net worth, runway, projections, properties, spending.
2. **The copilot** — every number in the app is served by a local FastAPI backend
   (`http://localhost:8000/docs`). Point [Claude Code](https://claude.com/claude-code) at it
   and you have a financial analyst with full access to *your* data: ad-hoc questions,
   scenario stress-tests, spending audits, tax-year prep. This is the feature the dashboard
   is just the front end for. See [docs/CLAUDE_CODE_USAGE.md](docs/CLAUDE_CODE_USAGE.md).

## Monarch by design

FIREMaster does **not** connect to your banks. [Monarch Money](https://www.monarchmoney.com)
(~$8/month) owns aggregation — bank connections, transaction dedup, merchant cleanup,
categories — because that's a hard, thankless problem that a dedicated product already solves
well. FIREMaster syncs from Monarch and owns everything Monarch doesn't: FIRE projections,
scenario math, property P&L, bridge planning, and the AI-analyst layer.

This is a deliberate two-layer architecture, not a missing feature. It also means you don't
need Monarch to try the app:

- **Day one (no Monarch):** seed the built-in demo persona and every page renders alive —
  a 52-year-old fresh off a layoff, three properties, a SEPP bridge plan, and a cash crunch
  the projections catch before it happens.
- **When you're ready:** connect your Monarch account and sync your real data. Demo rows are
  manual-source, so they survive alongside a real sync until you remove them with one command.

## Quick start

Prerequisites: [Docker Desktop](https://www.docker.com/products/docker-desktop/),
[uv](https://docs.astral.sh/uv/), Node 18+, and git. macOS or Linux; on Windows use WSL2
(recommended) or Git Bash — the setup scripts are bash scripts.

```bash
git clone <this-repo> firemaster && cd firemaster

./scripts/setup.sh      # generates backend/.env: JWT secret + your admin password
./scripts/start.sh      # postgres + redis (Docker), migrations, backend, worker, frontend
```

Then, in a second terminal — seed the demo persona and look around:

```bash
cd backend
uv run python ../scripts/seed_demo.py        # full demo financial life, every page alive
uv run python ../scripts/seed_scenarios.py   # optional: example what-if scenarios
```

Open **http://localhost:5173**, log in as `admin` with the password you chose, and start with
the Dashboard and Retirement pages. The demo is safe to explore, re-seed, or remove
(`seed_demo.py --remove`) at any time.

### Going live with your data

```bash
cd backend
uv run python ../scripts/monarch_login.py    # one-time Monarch auth (email/password/MFA)
```

Then hit **Sync Now** on the Dashboard. Full walkthrough — including account enrichment,
property rules, and your first FIRE config — in [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)
and [docs/MONARCH_SETUP.md](docs/MONARCH_SETUP.md).

## What's inside

| Page | What it does |
|---|---|
| Dashboard | Net worth, asset/liability allocation, history, one-click Monarch sync |
| Runway | Cash runway: months of burn covered, income vs. spend, upcoming cashflow events |
| Retirement | Wealth-pool projection to age 90+, scenario compare, SEPP bridge, FIRE number |
| Assets | Asset hub with enrichment: FIRE roles, strategies, notes per account |
| Spending | Spending analyzer by category/merchant over time |
| Tracker | Monthly non-property spending vs. target, category drill-down |
| Transactions | Full ledger browser: filter, classify, assign to properties |
| Properties | Per-property P&L from real transactions (rules + overrides + Monarch tags) |
| Tax Planning | Effective tax modeling for retirement drawdown |

Under the hood: Python 3.12 / FastAPI / SQLAlchemy 2.0 async / PostgreSQL 16 / Celery + Redis,
React 18 + TypeScript / Vite / Tailwind. All money is integer cents; all projection rates are
real (after-inflation). The test suite (`cd backend && uv run pytest`) covers the projection
engine, tax math, scenario merging, and property classification.

## Troubleshooting

- **`Docker daemon is not running`** — start Docker Desktop first; `start.sh` checks.
- **Port already in use** — the stack owns 5432, 6379, 8000, 5173. `start.sh` clears 8000/5173;
  stop other Postgres/Redis instances or change the compose port mappings.
- **bcrypt errors on Windows** — run setup under WSL2 or Git Bash with Python 3.12 x64 so a
  prebuilt `bcrypt` wheel is used. FIREMaster calls `bcrypt` directly (not passlib, which is
  incompatible with bcrypt 5.x) — if `setup.sh` can't hash your password, your venv likely
  failed to install bcrypt; re-run `uv sync` inside `backend/` and watch for wheel errors.
- **Changed `backend/.env` but nothing happened** — settings are cached at process start;
  restart the backend (and the Celery worker).
- **Edited engine code but Celery behaves old** — the worker doesn't hot-reload; restart it.
- **Stack was offline for weeks** — incremental sync looks back 45 days. For longer gaps, run a
  backfill: see "Monarch sync" in [docs/MONARCH_SETUP.md](docs/MONARCH_SETUP.md).

## Why this exists

I spent twenty-five years building technology for movies and games — the kind of career you
don't plan an early exit from, until a layoff plans it for you. At 52, with a household that
runs on real estate as much as index funds, every retirement calculator I tried gave me a
polite shrug: none of them could model a severance runway, a 72(t) bridge, a rental that pays
for itself, or the one question that actually mattered — *which year does cash go negative,
and what fixes it?* So I built the tool I needed, on top of the data I already had. FIREMaster
is that tool, cleaned up so you can run it on yours.

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — design philosophy, the two-interface model, projection engine internals
- [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) — full installation walkthrough
- [docs/MONARCH_SETUP.md](docs/MONARCH_SETUP.md) — connecting and syncing Monarch Money
- [docs/CLAUDE_CODE_USAGE.md](docs/CLAUDE_CODE_USAGE.md) — the AI-analyst workflow, with example prompts
- [docs/PROPERTY_MODULE.md](docs/PROPERTY_MODULE.md) — property P&L classification internals
- [CLAUDE.md](CLAUDE.md) — repo guide for Claude Code sessions
