# Property Module — Reference

*Quick reference for how the Properties module classifies transactions and what the controls do. Code lives in `backend/app/engines/property_pnl.py`, page at `/properties` (`frontend/src/pages/PropertyPnLPage.tsx`).*

---

## What it does

The module maps **every transaction → which property + whether it's income or which type of expense**. That mapping drives the per-property P&L (rental income, costs by category, net/yr, cost-per-equity).

The catch: Monarch only sees merchant text ("Lender A Mortgage," "Airbnb," "Venmo") — it has no idea about your properties. So the module keeps **rules** that translate merchant → property + category, and stamps the answer onto each transaction (`property_id`, `property_category`, `property_source`).

> **Mental model:** rules = source code, transactions = input, classifications = build output. **Re-classify recompiles.**

---

## 🔄 Re-classify

**What:** re-runs the classifier over your whole transaction history and re-stamps each row.

**How it decides** (per transaction, in priority order):

1. **Exclusions** (your auto/life insurers, anything personal that looks property-ish) → never a property charge.
2. **Income rules** on deposits (positive amounts) → Rental Income (Airbnb, property managers, tenants).
   *Skips credit-card rows — a positive Airbnb on a credit card is a guest refund (a trip you booked), not a host payout. Host payouts only land in checking.*
3. **Expense rules** on charges (negative amounts) → Mortgage / HOA / Utilities / Moorage / Insurance / Property Tax / Repairs…
4. **Monarch tags** → a transaction tagged with a property's name in Monarch maps to that property (lets you classify things with no merchant signal, e.g. a Venmo deposit).

**Precedence:** manual override **>** Monarch tag **>** merchant rule.

**Why / when you press it:**

- It runs **automatically after every Monarch sync** — day to day you never touch it.
- The button is the **"apply my changes now"** trigger: after you add/edit a rule or tag something in Monarch, press it to refresh the P&L without waiting for a sync.
- **Safe & idempotent:** re-running can't double-count. Rows you set by hand (`property_source = 'manual'`) are never touched, and deleting a rule cleanly un-assigns the rows it used to match on the next run. Returns a tally: `{matched, unmatched, skipped_manual}`.

**`property_source` values** ∈ `rule` · `manual` · `monarch_tag` · `NULL` (unassigned). The ledger shows a green "tag" badge for `monarch_tag`.

---

## ⚙️ Manage

A panel with three tabs — where you edit the *inputs* that Re-classify then applies:

1. **Classification rules** — add / edit / delete the merchant→property→category rules (the "source code").
2. **Property facts** — each property's worth, loan balance, rental potential, etc.
3. **Manual entries** — off-Monarch transactions & hand-overrides (e.g. a Venmo rent deposit, excluded Airbnb guest refunds).

**The loop:** edit in **Manage** → press **Re-classify** → P&L updates.

---

## Gotchas worth remembering

- **Rental income can't land on a credit card.** A positive "Airbnb" on a credit card is a *guest refund*, not a host payout. The income classifier skips credit-card rows for exactly this reason (a real reconciliation against an Airbnb host export caught months of guest refunds inflating rental income before this guard existed).
- **Manual rows are sacred.** `property_source = 'manual'` survives both Monarch re-sync and Re-classify. That's the override escape hatch — use it to exclude (`property = none`) or force-assign anything the rules get wrong.
- **P2P payments (Venmo, Zelle) never get auto-rules.** The merchant string carries no property signal — classify those per-transaction (manual override or a Monarch tag), never with a merchant rule.
- **Monarch tags are bidirectional.** Classifications can be mirrored to Monarch as tags (tag name = property name, via `scripts/monarch_tag_writeback.py`); a tag set in Monarch flows back into the P&L on the next Re-classify.
- **Celery runs Re-classify post-sync but doesn't hot-reload** — restart the worker after engine edits, or the auto path runs stale code. (The in-app button is current via uvicorn `--reload`.)
