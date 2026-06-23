# Using Claude Code as Your Financial Analyst

This is the feature the rest of the app exists to serve. The dashboard shows you state; an
AI agent with API access *answers questions*. FIREMaster's backend is a clean, documented
REST API over all of your financial data — point [Claude Code](https://claude.com/claude-code)
at it and you get an analyst that can pull any number, run any projection, cross-check any
assumption, and write you a report, on demand, locally.

Why this beats a chat-with-your-money widget baked into the app: an agent in your terminal
composes tools (API + math + files + scripts), keeps long-running context, writes artifacts
(reports, CSVs, charts), and improves every time the models do — with zero app code. The full
argument is in [ARCHITECTURE.md](../ARCHITECTURE.md).

## Setup (one minute)

1. Start the stack (`docker compose up`) and install
   [Claude Code](https://docs.claude.com/en/docs/claude-code).
2. Open a terminal **in this repo** and run `claude`. The checked-in [CLAUDE.md](../CLAUDE.md)
   already teaches it the module map, the API surface, and the data-layer gotchas (cents,
   real rates, displayBalance).
3. First message of a session, tell it to authenticate and explore, e.g.:

> Get a token from POST /api/auth/login (username "admin", ask me for the password — don't
> save it anywhere), then GET /api/fire/wealth-projection and orient yourself.

The API is localhost-only and JWT-gated; the OpenAPI explorer at
`http://localhost:8000/docs` is the same surface Claude discovers.

## The surface area

| Endpoint family | What Claude can pull |
|---|---|
| `/api/net-worth/*` | current net worth, allocation, full history |
| `/api/accounts` | every account with balances + FIRE-role enrichment |
| `/api/fire/config`, `/api/fire/scenarios` | every assumption in your plan; scenario overrides |
| `/api/fire/wealth-projection` | month-by-month pools: cash, IRAs, taxable, real estate, illiquid |
| `/api/fire/number`, `/milestones`, `/readiness`, `/bridge-status` | FIRE math + bridge health |
| `/api/fire/spending-sensitivity` | outcome vs. spending level |
| `/api/spending/*`, `/api/spending/tracker` | category/merchant spending, monthly target tracking |
| `/api/transactions` | the full ledger with filters |
| `/api/properties/*` | per-property P&L, classification rules |
| `/api/cashflow/*` | runway, income sources, future events |
| `/api/tax/*` | drawdown tax modeling |

Money is integer **cents** everywhere; projection rates are **real** (after-inflation).
Claude knows this from CLAUDE.md — but it's worth knowing yourself when you read its work.

## Prompts that earn their keep

Strategy and stress-testing:

- *"Pull the wealth projection. Which month does cash bottom out, what's driving it, and
  what's the cheapest fix — spending cut, earlier property sale, or starting SEPP sooner?
  Quantify each."*
- *"Compare every scenario's end-of-plan total and worst cash month in one table. Which
  single assumption moves the outcome most?"*
- *"Re-run the projection with spending $1,500/mo higher (spending_override param). Does the
  bridge to 59½ still hold? Where's the new break-even spending level?"*
- *"Sanity-check my config: list every custom_assumptions value and flag anything that looks
  inconsistent with the others or with current market assumptions. Don't change anything."*

Operations and audits:

- *"Audit this month vs my tracker target. Top 5 categories over their usual run-rate, with
  the specific transactions."*
- *"Pull last year's P&L for each property and draft the schedule-E-shaped summary I'd hand
  an accountant. Flag any income rows that look unclassified."*
- *"Find transactions that look like duplicates or missing classifications across the
  ledger."*
- *"Write me a one-page monthly review (markdown): net worth delta, burn vs plan, runway,
  projection drift since last month."*

Modeling work:

- *"Add a scenario: sell the income property in 18 months, proceeds to the taxable pool —
  use the property_sales mechanism, then compare it against the baseline."* (Claude can
  PATCH/POST via the API; it will show you the payload first.)

## Ground rules that work well

- **Read-mostly**: let Claude GET freely; have it show you any PATCH/POST payload before
  sending. Claude Code asks permission for commands by default.
- **Artifacts over chat**: ask for reports as markdown files in a `reports/` folder
  (gitignored) — they accumulate into a personal financial-review archive.
- **Don't paste secrets**: Claude only needs the admin password at login time (or mint a
  token yourself and hand it over). Your Monarch credentials never enter the picture — the
  session file is gitignored and Claude has no reason to touch it.
- The in-app AI advisor (`/api/advisor`) still exists but is de-prioritized — this workflow
  replaced it. You don't need an `ANTHROPIC_API_KEY` in `.env` for Claude Code.
