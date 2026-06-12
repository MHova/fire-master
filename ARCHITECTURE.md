# FIRE Master — Architecture & Design Philosophy

## The Core Insight

The defining architectural decision of FIRE Master emerged accidentally during development. The original spec positioned an in-app AI advisor (Claude API chat panel) as the platform's "key differentiator." But through building it, we discovered the real power architecture:

**Claude Code (Opus 4.6) is the primary analysis tool — not the in-app advisor.**

The in-app advisor is limited by design: constrained context window, predefined tool schemas, per-API-call costs, and a smaller model (Sonnet). Claude Code, by contrast, has full codebase access, can query any backend API directly, read and write files, execute scripts, iterate on analysis, and reason with the full power of Opus 4.6. The cost of the Anthropic API per call was the constraint that revealed the better design.

This isn't a workaround — it's the optimal architecture for a single-user power tool.

## The Two-Interface Architecture

FIRE Master is a two-interface application. Each interface does what it's best at:

- **The Frontend** handles display and data entry — dashboards, charts, enrichment forms, configuration.
- **Claude Code** handles analysis and planning — scenario modeling, tax strategy, personalized advice.

Neither is the "real" UI. They're complementary. The backend API layer is the shared abstraction boundary that both consume.

```
                        ┌─────────┐
                        │   You   │
                        └────┬────┘
                   ┌─────────┴─────────┐
                   │                    │
                   ▼                    ▼
        ┌─────────────────┐  ┌─────────────────┐
        │    Frontend      │  │   Claude Code    │
        │    (React)       │  │   (Opus 4.6)     │
        │                  │  │                   │
        │  ● Dashboards    │  │  ● Deep analysis  │
        │  ● Charts        │  │  ● Scenario runs  │
        │  ● Data entry    │  │  ● Tax strategy   │
        │  ● Enrichment    │  │  ● Ad-hoc queries  │
        │    forms         │  │  ● Planning        │
        │                  │  │  ● Code + scripts  │
        │  DISPLAY +       │  │                   │
        │  DATA ENTRY      │  │  ANALYSIS +       │
        │                  │  │  PLANNING          │
        └────────┬─────────┘  └────────┬──────────┘
                 │                      │
                 │    REST API layer     │
                 └──────────┬───────────┘
                            │
              ┌─────────────▼─────────────┐
              │      Backend (FastAPI)     │
              │                            │
              │  Engines:                  │
              │   net_worth  spending      │
              │   fire_proj  tax_engine    │
              │   monte_carlo  asset_hub   │
              │                            │
              │  Ingestion:                │
              │   monarch_sync             │
              │   category_sync            │
              │                            │
              │  Tasks:                    │
              │   celery (4hr sync,        │
              │   daily snapshot)           │
              ├────────────────────────────┤
              │    PostgreSQL + Redis       │
              │                            │
              │  Accounts + enrichment     │
              │  Transactions              │
              │  Balance snapshots         │
              │  FIRE config + income      │
              │  Goals + tax config        │
              └────────────────────────────┘
```

### The workflow in practice

1. **You enter enrichment data in the frontend** — notes, FIRE roles, strategies, tags, targets for each account. Configure FIRE assumptions (retirement age, SWR, life expectancy, income sources). This is the knowledge base.

2. **The backend stores and computes** — Monarch syncs raw financial data (accounts, transactions, balances). Engines compute net worth, spending analysis, FIRE projections, scenarios, readiness scores. All exposed via rich REST APIs.

3. **Claude Code queries the backend for deep analysis** — in conversation, Claude Code calls the APIs (`/api/fire/metrics`, `/api/fire/scenario`, `/api/tax/roth-conversion-plan`, etc.), reads the enrichment data, runs scenarios, and provides personalized, data-grounded advice. It can also write new scripts, run ad-hoc SQL, or build one-off analysis tools — things no predefined chat UI could do.

4. **The frontend displays results** — dashboards, charts, projections. The lifetime projection chart, the Monte Carlo fan chart, the FIRE countdown, the readiness score. Visual feedback, not the analysis itself.

### What makes this different from a normal app

Most applications have one UI. FIRE Master has two, and they're asymmetric:

| Capability | Frontend | Claude Code |
|-----------|----------|-------------|
| View dashboards & charts | Yes | No |
| Enter enrichment data | Yes | Can, via API |
| Run predefined projections | Yes (button click) | Yes (API call) |
| Run custom scenarios | Limited (config page) | Unlimited (any parameters) |
| Cross-reference data sources | No | Yes (queries multiple APIs) |
| Explain results in natural language | No | Yes |
| Write new analysis on the fly | No | Yes |
| Remember context across conversation | No | Yes (conversation context) |
| Access account enrichment notes | Display only | Read + reason about |
| Tax strategy recommendations | Display tables | Personalized analysis |

The frontend is the **cockpit** — you glance at it to see where you stand. Claude Code is the **co-pilot** — you talk to it when you need to think through a decision.

## Why This Works Better Than the Alternatives

### vs. In-App AI Advisor
The in-app advisor (Phase 3) works but is fundamentally limited:
- Fixed tool schemas — can only query what we pre-defined
- Per-API-call costs (Anthropic billing)
- Smaller model (Sonnet vs Opus)
- Can't read files, write code, or iterate
- No memory across sessions beyond conversation history

Claude Code has none of these limitations. It can run any query, write new analysis scripts, access the full codebase, and reason about the complete financial picture.

### vs. ProjectionLab / Boldin
The spec originally planned integrations with ProjectionLab (browser-based Plugin API) and Boldin (manual CSV import). Both were cancelled because:
- **ProjectionLab**: Would require fragile browser automation. Our own projections engine covers ~80% of its value. The remaining 20% (tax optimization, Monte Carlo) is now built in Phase 6.
- **Boldin**: Manual CSV import adds complexity for validation data. You can use Boldin directly for cross-validation without importing.
- **Neither tool** lets you sit with an AI analyst who can see your account enrichment, run custom scenarios, and give specific recommendations. That's what Claude Code provides.
- **The real gap**: These tools answer "what does the math say?" Claude Code answers "what should *you* do, given everything I know about your accounts, strategy, tax situation, and goals?" The enrichment layer is what makes that possible.

### vs. Traditional Financial Software
Mint, YNAB, Personal Capital — all consumer tools optimized for mass market. FIRE Master is a single-user power tool optimized for one person's specific FIRE journey. The information density, the enrichment system, the draw-down FIRE rule, the lifetime projections — none of this exists in consumer tools.

## Key Design Decisions

### Draw-Down-to-Zero FIRE Rule
Instead of the traditional 4% perpetual rule (which preserves principal forever, leaving millions behind), FIRE Master uses a draw-down-to-target-legacy calculation:

```
PV = W × [(1 - (1+r)^(-n)) / r] + legacy × (1+r)^(-n)

W = net annual withdrawal (spending - post-retirement income)
r = real return rate (nominal - inflation)
n = years in retirement (life_expectancy - retirement_age)
legacy = target amount to leave behind ($0 = spend it all)
```

Philosophy: live a rich life, retire early, spend it all. The traditional rule is available for comparison but not the default.

### Account Enrichment as Knowledge Base
Every Monarch account can be annotated with:
- **FIRE role**: core retirement, bridge account, emergency fund, growth, operating
- **Notes**: free-form knowledge (employer match %, vesting schedules, rules)
- **Strategy**: investment approach, contribution plan, rebalancing notes
- **Tags**: user-defined grouping (tax-advantaged, bridge, etc.)
- **Targets**: target balance, target allocation percentage
- **Custom data**: structured key-value pairs (expense ratios, auto-transfer rules)

This enrichment is preserved across Monarch syncs and compounds the value of every Claude Code conversation. The more you annotate, the deeper the analysis can go.

### Backend-First, Frontend-Light
Every new capability starts as a backend engine with API endpoints. The frontend gets a simple display page. Complex analysis happens in Claude Code conversations, not in the UI. This keeps the frontend clean and the backend rich.

## The Compounding Effect

Each phase builds on the previous:
- **Phase 1** (Monarch sync) → raw financial data
- **Phase 2** (Spending engine) → spending patterns and savings rate
- **Phase 3** (AI advisor) → proved the concept, revealed its own limitation
- **Phase 4** (Account enrichment) → personal knowledge attached to every account
- **Phase 5** (FIRE projections) → lifetime modeling using all the data + knowledge
- **Phase 6** (Tax engine) → tax-aware optimization using account types + enrichment

The enrichment data from Phase 4 makes Phase 5 projections smarter. Phase 5's scenario engine makes Phase 6's tax optimization possible. And Claude Code, sitting in the middle, gets more powerful with every piece of data you add.

This is a flywheel: more data → better analysis → better decisions → more confidence in the tool → more data entered.

## Projection Engine: Spending & Funding Waterfall

The core of the retirement projection (`project_wealth_pools()` in `fire_projections.py`) simulates month-by-month cash flows across wealth pools: Cash, IRA-A (SEPP), IRA-B (growth), RRSP/RRIF, Real Estate, and — in scenarios that sell property into the market — a Taxable brokerage pool. Understanding the funding waterfall is essential to interpreting projection results.

### Monthly Expense Formula

Spending varies by life phase and property ownership:

```
Phase 0 (before any sales):
  expenses = base_burn × spending_mult(age) + healthcare

Phase 1 (after the income property sells, legacy sauvie_sale block):
  expenses = (base_burn - mortgage_pi - income_property_cost) × spending_mult(age) + healthcare

Phase 2 (after the primary property sells, legacy miami_sale block):
  expenses = (base_burn - primary_property_cost + post_sale_rent) × spending_mult(age) + healthcare
```

With the generic `property_sales` mechanism (below), the per-phase deltas come from each
sale entry's `monthly_cost` / `post_sale_rent` / `in_base_burn` instead of the legacy blocks.

Where `spending_mult(age)` is the Blanchett spending curve:
- **Go-go** (< age 70): 100% — travel, active lifestyle
- **Slow-go** (70–80): 85% — reduced activity
- **No-go** (80+): 75% — minimal discretionary

Healthcare (`healthcare_monthly_cost`) is additive and only applies pre-Medicare (before age 65). All rates and ages are configurable via `custom_assumptions.projection`.

### Monthly Funding Waterfall

Each month, expenses are funded through this sequence:

1. **Income arrives** — rental income from DB income sources, STR income, cashflow events (severance, planned sales, windfalls)
2. **Fixed draws execute** — SEPP from IRA-A and RRSP/RRIF (amounts + start months from `custom_assumptions.sepp` / `.rrsp`; inactive unless configured)
3. **Social Security starts** — at configured claim age (default 62), reduced for early claiming (70% of full)
4. **Net applied to cash** — income + draws - expenses → cash pool increases or decreases
5. **Taxable, then IRA-B, backstop** — when cash falls below its ~12-month reserve, the taxable brokerage (if funded by property sales) is drawn first (penalty-free at any age); after 59½, IRA-B covers any residual gap
6. **Surplus invested** — cash above 12-month reserve earns investment return (4% real)
7. **Cash can go negative** — the model allows it to show bridge stress; frontend clamps display at $0

### Why This Matters for Spending Sensitivity

Changing monthly spending doesn't pull from a specific account — it changes the monthly gap between income and expenses. A larger gap drains cash faster, which triggers IRA-B draws sooner, which reduces compound growth on that pool. The effect cascades: an extra $1,000/mo of spending costs hundreds of thousands at the horizon, because the extra draw compounds for decades.

The spending sensitivity card on the Retirement page exploits this: adjusting the base spending number reruns the projection, and the sensitivity strip shows the relationship between spending level and terminal wealth. Cash crisis months (when cash first goes negative) make the bridge risk visible.

### Generic Property Sales + Taxable Brokerage Pool

The original engine hardcoded three property sales as bespoke code paths. They're now unified into one config-driven mechanism via `custom_assumptions.property_sales` — a list with one entry per sale. When present it supersedes the legacy per-property blocks entirely (all-or-nothing, so no double-sell); scenarios without it run the legacy path unchanged. The legacy blocks (`miami_sale`, `sauvie_sale`, `str_income`, `mortgage_recast`) are retained for author back-compat only — do not use them in new configs.

Each sale entry models:
- **Dynamic proceeds** — appreciated `value` (real appreciation to the sale month) minus `agent_fee_pct`, minus capital-gains tax (`ltcg_rate` + `state_tax_rate` on the gain over `cost_basis`, less any `section_121_exclusion`), minus the mortgage payoff (static `mortgage_balance_at_sale`, or amortized from `current_mortgage_balance` + `mortgage_rate` + `mortgage_pi`).
- **Burn/income deltas** — a carrying cost already inside `target_annual_spending` is removed at sale; a cost that was never in the budget (a property the budget assumed already sold) sets `in_base_burn=False` so it's *added* while held and removed at sale. Rental income flows from the DB income source (which has no sale-aware end date), so `monthly_income` *cancels* it at sale (×`rental_occupancy_rate` when `occupancy_adjusted`) rather than adding it while held. `suppress_cashflow_match` drops a planned cashflow event the sale replaces (e.g. a manual "… Sale Proceeds" event) to avoid double-counting.
- **Proceeds routing** — `proceeds_to: "taxable"` sends net proceeds into a new **taxable brokerage pool** (`custom_assumptions.taxable_pool` = `{starting_balance, return_rate}`, real rate); `"cash"` keeps the legacy behavior. Keep the taxable `return_rate` ≤ the IRA's 6% real rate: a taxable account holding the same index nets *less* than the tax-deferred IRA after dividend/turnover tax, so it must not out-earn it.

The taxable pool is the 6th pool in the funding waterfall and is drawn **before** IRA-B (it's penalty-free at any age) — see step 5 above. That ordering is what lets a scenario test whether 72(t)/SEPP is still needed: set `sepp.sepp_monthly = 0` and check whether the taxable pool alone keeps cash positive to 59½. (`WealthPoolPoint` carries `taxable` and `taxable_draw`; both feed `total` and the teal band on the Retirement chart.)

**Month-0 hygiene** (related fix): one-off cashflow events dated before today are dropped rather than clamped to month 0 — otherwise a finished severance or paid expense reappears as a phantom month-0 flow. Recurring events start from today. (Known limitation: the day-based bucketing rounds events <~30 days out to month 0.)

## Known Inconsistency: Dual Cash Runway Calculations

Two modules compute cash runway with different assumptions — they will give different answers:

| | Retirement Page (`bridge-status`) | Runway Module (`cashflow/runway`) |
|---|---|---|
| **Engine** | `FireProjectionsEngine.compute_bridge_status()` | `CashflowEngine.project_runway()` |
| **Income** | Ongoing sources only (excludes temporary) | User overrides or trailing 3-month average (all income) |
| **IRA/SEPP** | Only if start month reached | Not modeled |
| **Burn rate** | Trailing 12-month actuals or config override | User override or trailing 3-month average |
| **Stance** | Conservative (worst-case bridge stress) | Scenario-based (user-controlled assumptions) |

This is intentional for now — Retirement page is the conservative "am I okay?" gauge, Runway module is the interactive "what if?" tool. Future work: consider unifying or at least surfacing the assumption difference in the UI so the numbers don't confuse at a glance.

## What This Means Going Forward

The architecture implies a clear priority order for future work:

1. **Data entry first** — The enrichment layer is the bottleneck. Every account annotated, every FIRE config field filled, every income source modeled makes Claude Code conversations exponentially richer. Frontend forms for data entry are high-leverage.

2. **Backend engines second** — New computational capabilities (physical assets, SS optimization, Roth conversion timing) should be built as backend modules with API endpoints. Claude Code consumes them immediately. No frontend needed to get value.

3. **Frontend visualization third** — Dashboard charts and pages are nice but not where the insight happens. Build them when you want to glance at something without starting a Claude Code conversation.

4. **In-app advisor last** — It works, it's there if you want a quick lookup, but it will never match Claude Code's depth. Don't invest more here.

The system passes a tipping point once the data compounds: accounts enriched, years of transaction history synced, the tax engine and Monte Carlo running — at that point the Claude Code conversations write themselves. The question isn't "can the tool answer my FIRE questions?" It's "what questions haven't I asked yet?"
