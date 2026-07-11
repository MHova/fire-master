# FIREMaster — Claude Code analyst context

You are the analysis layer for FIREMaster, a personal FIRE (financial independence) planning
app running locally on this machine. The app's REST API at **http://localhost:8000** is the
real product — the web UI is just one view of it. Your job: authenticate, pull any number, run
projections, set up the user's data on request, and write reports/CSVs locally.

The user opened this folder (the FIREMaster starter kit) and has the app running via
`docker compose up`. There is **no application source code here** — just this file, the compose
file, and guides. You work entirely through the HTTP API.

## Connect (do this first)

1. **Authenticate.** `POST http://localhost:8000/api/auth/login` with JSON
   `{"username": "admin", "password": "<ASK THE USER>"}`. **Ask the user for the password each
   session; never write it to a file.** The response is `{"access_token": "..."}`.
2. **Use the token** on every other call as a header: `Authorization: Bearer <access_token>`.
3. **Orient.** The full, always-current API is at **http://localhost:8000/openapi.json** — fetch
   it to see every endpoint and request/response shape. Human-readable: http://localhost:8000/docs.
   A good first pull is `GET /api/fire/wealth-projection` (the headline projection).

## Data gotchas (NOT visible in the OpenAPI schema — read these)

- **Money is integer cents** (BIGINT) almost everywhere: account balances, targets, transactions,
  income, config dollar amounts. Divide by 100 for dollars; multiply by 100 when writing.
- **Exception: the Properties API uses dollars as floats** (`value`, `loan_balance`,
  `purchase_price`). Don't multiply those by 100.
- **Use `displayBalance`, not `currentBalance`** for an account's balance.
- **Projection rates are REAL (after-inflation).** Flat spending = constant purchasing power; a
  flat Social Security number assumes COLA offsets inflation. Don't "add inflation" on top.
- When unsure of a field's units or allowed values, **GET an existing record first** and mirror
  its shape rather than guessing.

## Setting up the user's data (the three common tasks)

After a user connects Monarch, accounts/transactions import automatically but **enrichment,
scenarios, and property classification do not** — there's no UI for some of these, so this is
where you earn your keep. Always confirm changes with the user before writing.

### 1. Enrich accounts
`PATCH /api/accounts/{account_id}/enrichment` — body fields (all optional, send only what changes):
`notes` (str), `tags` (list[str]), `fire_role` (str — how the account is treated in projections;
GET an account or the projection to see the roles in use), `target_balance` (cents),
`target_allocation_pct` (float), `strategy` (str), `custom_data` (object).
Get account IDs from `GET /api/accounts`. Enrichment **survives Monarch re-syncs** — it's yours.

### 2. Scenarios (what-if planning)
A scenario is a set of **overrides deep-merged onto the base FIRE config**. Workflow:
1. `GET /api/fire/config` — read the *exact* current config shape (assumptions, projection rates,
   spending, property-sale blocks, etc.). Your overrides must mirror these keys.
2. `POST /api/fire/scenarios` with `{"name": "...", "description": "...", "overrides": { ...only
   the keys you want to change, same nesting as the config... }}`.
3. Activate with `POST /api/fire/scenarios/{id}/activate` (one active at a time;
   `POST /api/fire/scenarios/deactivate` to clear). Re-pull `GET /api/fire/wealth-projection` to
   see the effect.
Tip: most knobs live under `custom_assumptions.projection` (all rates real). Read the config to
see what's there before composing an override — never invent keys that aren't in it.

### 3. Properties (only if the user owns property)
Two pieces: the property record, then merchant **rules** that classify transactions to it.
1. `POST /api/properties` — `{"key": "river-house", "name": "River House", "value": 450000,
   "loan_balance": 280000, ...}`. **Dollars, not cents** here. `key` is a short slug.
2. `POST /api/properties/rules` — `{"property_id": "<uuid>", "pattern": "HOME DEPOT",
   "match_type": "merchant_substring", "rule_kind": "expense" | "income" | "exclusion",
   "expense_category": "Maintenance", "priority": 100}`. The `pattern` matches the merchant name.
3. `POST /api/properties/reclassify` — **required** to apply rules to existing transactions
   (rules don't act retroactively until you run this).
Notes that matter: rental **income never lands on a credit card** (a positive amount there is a
guest refund, not a payout). P2P payments (Venmo/Zelle) carry no merchant signal — classify those
per-transaction (`PUT /api/properties/transactions/{tx_id}`), not with an auto-rule.

## Analysis & reports
You can pull anything (`/api/fire/*`, `/api/spending/*`, `/api/properties`, `/api/tax/*`,
`/api/transactions`) and write the user local artifacts — markdown reports, CSVs, charts. That
composability (API + math + files, with memory across a session) is the whole point of using an
agent here instead of a chat box bolted into the app.

Notable tax endpoints:
- `GET /api/tax/sepp?balance=&age=&rate=[&target_monthly=&afr_120=]` — SEPP/72(t) calculator
  (Rev. Rul. 2002-62 / Notice 2022-6). Forward: payment per IRS method (fixed amortization,
  RMD method; post-2022 Single Life Table). Reverse: `target_monthly` → the IRA-A balance that
  yields it (the dual-IRA split). Rate is capped at max(5%, 120% of the federal mid-term AFR).
  Feed the result into `custom_assumptions.sepp` (`sepp_monthly`, `ira_a_balance`) to drive
  the wealth projection's SEPP bridge.
- `GET /api/tax/withdrawal-plan?years=&target_bracket=&roth_conversions=` — tax-aware
  withdrawal sequencing with golden-window bracket-fill Roth conversions.
