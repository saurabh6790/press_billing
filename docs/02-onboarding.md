# 02 — Onboarding

This gets a newcomer from a clean bench to a running system with realistic demo
data, in order. Allow ~10 minutes.

## Prerequisites

- A working Frappe **bench** (the dev bench used here is
  `/Users/frappe/workspace-2/dev-bench`, Frappe 17-dev, Python 3.14).
- Node + `yarn` (for the dashboard SPA build).
- No live gateway credentials are needed — charges/refunds/webhooks run in test
  mode.

## Install the app

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app billing $URL_OF_THIS_REPO --branch fc-prod
bench --site billing.local install-app billing
```

> Gateway SDKs (`stripe>=15`, `razorpay`) are declared in the app's
> `pyproject.toml` and installed with the app. PayPal needs no SDK (pure REST).

## Stand up the full demo (recommended first run)

The demo seeds ten teams across every tier, currency, region and account state —
the fastest way to *see* the whole system working.

```bash
cd /Users/frappe/workspace-2/dev-bench

# 1. Migrate both apps (Central + Agent)
bench --site billing.local migrate
bench --site agent.local   migrate

# 2. Build the customer/admin SPA (Frappe-UI)
cd apps/billing/dashboard && yarn install && yarn build && cd -

# 3. Seed demo data on both sites
bench --site billing.local execute billing.demo.demo_scenarios.seed_all
bench --site agent.local   execute press_billing_agent.demo.seed

# 4. Run the server
bench start
```

`migrate` runs the app's `after_migrate` hooks, which create the two billing
roles (`Billing Admin`, `Billing User`) and the `User.billing_team` link field —
so authorisation works immediately. See
[04 — Configuration](04-configuration.md).

## What the seed gives you

- **3 clusters**: `in-mumbai` (India), `eu-frankfurt` (EU), `me-dubai` (ME).
- **5 plan sizes** (1→16 vCPU), each priced per cluster × currency (INR/EUR/USD).
- **4 trust tiers** (`t0` trial → `t3` enterprise) with rising caps.
- **1 metered add-on**: Bandwidth Overage, priced per GB per currency.
- **10 teams**, each chosen to demonstrate one behaviour:

| Team | Tier | Currency | Demonstrates |
|---|---|---|---|
| `acme-corp` | t3 | INR | **Grandfathering** — locked ₹9,360 vs ₹12,000 catalog; multi-region |
| `globex` | t3 | EUR | Enterprise, €-billed, 10-month history |
| `initech` | t2 | USD | Growth tier, $-billed |
| `umbrella` | t2 | INR | **Cross-region** — INR team running in EU + India |
| `wayne-ent` | t2 | INR | Cross-region on a **Razorpay UPI mandate** |
| `stark-ind` | t1 | INR | **Dunning** — `past_due`, 3 failed retries, still running |
| `cyberdyne` | t1 | EUR | **Suspended** + cap-0 suspend token |
| `hooli` | t1 | INR | Prepaid credits → **shortfall alert** |
| `soylent` | t1 | USD | **Refund** — partial overcharge → wallet |
| `piedpiper` | t0 | INR | **Free trial** — computed, not charged |

## First steps — three surfaces to open

### 1. The Desk data model

`http://billing.local:8000/app/billing` (log in as **Administrator**).

The **Billing** workspace links every DocType: Invoices, Price Lock, Credit
Ledger, Payment Methods, Catalog & Config. Open the open June **in-mumbai**
invoice on `acme-corp` to see fixed plan lines + a metered overage line + GST —
all computed from the Agent's event log × locked prices.

### 2. The customer portal

`http://billing.local:8000/billing` — the Frappe-UI SPA. A **team switcher**
(top of the sidebar) flips between the ten demo teams, and a **customer ⇄ admin**
toggle swaps shells. Amounts render in each team's own currency.

Tabs: **Overview**, **Forecast**, **Invoices**, **Payment Methods**, **Credits**.
Every endpoint is auto-scoped to the caller's team.

### 3. The admin console

`http://billing.local:8000/billing/admin` — gated to the `Billing Admin` role.
**Overview** (MRR, delinquency, suspensions), **Teams** (per-team drill-down),
**Analytics** (payment failures, cluster/plan consumption, trial subsidy,
conversion).

### Bonus — the Agent operator view

`http://agent.local:8000/cluster` — the cluster-side mirror: Event Log, Usage
Meters, Plan Cache, Entitlements (running / stopped / terminated), Sync Log.

## Verify your install

```bash
cd /Users/frappe/workspace-2/dev-bench
bench --site billing.local run-tests --app billing
bench --site agent.local   run-tests --app press_billing_agent
```

All tests are integration tests (TDD throughout), including real multi-threaded
concurrency proofs: credit double-spend prevention, parallel invoice open,
concurrent webhook flood (exactly one stored), and offline Ed25519 token
verification on the Agent.

## Re-seeding / cleaning up

`seed_all` wipes and rebuilds the demo data each run, so it is safe to re-run
after code changes. If you only changed the frontend, just re-run
`yarn build` in `apps/billing/dashboard`.

Next: [03 — Architecture](03-architecture.md).
