# 06 — Actions & API reference

Every action a human or system can trigger, grouped by who calls it. All HTTP
endpoints are Frappe whitelisted methods, callable at
`/api/method/<dotted.path>`. Customer endpoints are auto-scoped to the caller's
team; admin endpoints require the `Billing Admin` role (standalone) or
`System Manager` operator bypass (merged into Central). Merged, customer reads
require the `billing:view` capability and mutations require `billing:manage` —
see [08 — Merging into Central](08-merge-into-central.md).

---

## Customer portal actions

Path prefix: `billing.api.dashboard.<module>.<fn>`. Used by the `/billing` SPA.

### Account (`account.py`)

| Endpoint | Does |
|---|---|
| `whoami` | The current user + their team. |
| `list_switchable_teams` | Teams the user (or admin/demo) may switch to. |
| `get_team_overview` | Overview card: tier, cap, standing, instances, currency, projection. |
| `get_trust_tier` | The team's tier, caps and promotion progress. |
| `get_billing_profile` / `save_billing_profile` | Read/write the team's billing profile. |
| `get_billing_settings` / `save_billing_settings` | Read/write billing preferences. |

### Invoices, forecast & credits (`invoices.py`)

| Endpoint | Does |
|---|---|
| `get_forecast` | Itemised month-end projection (services + metered overage, tax). |
| `list_subscriptions` | The team's subscriptions (one per region). |
| `list_invoices` / `get_invoice` | Invoice history / one itemised invoice. |
| `list_payment_attempts` | Attempts against an invoice. |
| `get_credit_balance` / `credit_ledger` | Wallet balance / full ledger. |
| `pay_invoice` | Customer-initiated pay of an open invoice. |
| `purchase_credits` | Buy wallet credits. |
| `create_topup_order` / `confirm_topup` | Two-step gateway top-up (order → confirm). |

### Payment methods (`methods.py`)

| Endpoint | Does |
|---|---|
| `list_payment_methods` | Methods on file. |
| `get_payment_method_options` | Which gateways/methods the team may add. |
| `initiate_card_setup` / `confirm_card` | Add a card (SetupIntent → confirm). |
| `setup_payment_method_order` / `confirm_payment_method_order` | Generic add-method order flow. |
| `add_demo_card` | Add a test card (demo only). |
| `set_default_payment_method` | Make a method the default. |
| `reorder_payment_methods` | Set fallback priority order. |
| `remove_payment_method` | Remove a method. |

---

## Admin console actions

Path prefix: `billing.api.admin.<module>.<fn>`. All require `Billing Admin`.

### Revenue (`revenue.py`)

`get_summary` (MRR, on-time vs delinquent, suspensions, failures) ·
`get_revenue_trend` · `get_cluster_breakdown` · `get_team_breakdown` ·
`get_payment_analytics` · `get_overdue_aging` · `get_free_trial_costs` ·
`list_all_invoices`.

### Teams (`teams.py`)

`list_teams` · `get_team_billing` (drill into one team) · `get_metrics` ·
`get_retention` · `get_payment_failures` · `get_delinquent_teams`.

### Catalog (`catalog.py`)

| Endpoint | Does |
|---|---|
| `get_catalog` | The full plan × cluster × currency rate table. |
| `update_plan_rate` | **Change a plan's rate** — writes a new Catalog Rate; existing price-locks untouched (grandfathering). |
| `get_cluster_consumption` / `get_plan_consumption` | INR-normalised run-rate by cluster / plan. |
| `get_conversion` | Trial → paid conversion rate. |
| `get_trial_detail` / `get_trial_costs_detail` | Trial subsidy breakdowns. |

---

## Operator / Desk actions

These run from the Desk form or controller, not the SPA.

| Action | Where | Does |
|---|---|---|
| **Revalidate & register webhook** | Payment Gateway form | `revalidate_and_register_webhook` — re-check keys, recreate webhook endpoint, rotate secret. |
| `update_plan_rate` | Admin catalog | Publish a new Catalog Rate (does not re-price existing locks). |
| `adjust_credits` | `billing.revenue.credits.adjust_credits` | Manual ledger adjustment (append-only). |
| Convert trial → paid | `billing.catalog.trials` | Flip `cost_report` invoices to `billable`. |

---

## System / inbound endpoints

Called by gateways and the Agent — **not** by a browser session.

### Gateway webhooks (`payments/webhooks.py`)

| Endpoint | Source |
|---|---|
| `billing.payments.webhooks.stripe` | Stripe webhook (signature-first). |
| `billing.payments.webhooks.razorpay` | Razorpay webhook (signature-first). |

Both verify the HMAC signature as the **first** operation and dedupe on
`gateway_event_id`. A bad signature → HTTP 400 with zero DB writes.

### Agent sync (`platform/sync.py`)

| Endpoint | Direction | Does |
|---|---|---|
| `push_plans_to_agent` | Central → Agent | Push plan definitions + display price to a cluster's Plan Cache. |
| `receive_usage_events` | Agent → Central | Ingest the event log (subscribed/changed/cancelled). |
| `receive_meter_rollups` | Agent → Central | Ingest metered usage rollups. |

The Agent authenticates with its API key, which holds **no** billing role — so it
can reach only this sync surface, never a customer/admin endpoint.

---

## Scheduled jobs (no caller — cron)

See [04 — Configuration §6](04-configuration.md) for the full table:
`run_dunning`, `run_reconciliation`, `cleanup_payment_logs` (daily);
`retry_failed_syncs` (hourly); `expire_payment_methods` (monthly).

---

## CLI / bench actions

```bash
# Migrate (also creates roles + the User.billing_team field)
bench --site billing.local migrate

# Seed / reset the full demo dataset
bench --site billing.local execute billing.demo.demo_scenarios.seed_all

# Run the test suite
bench --site billing.local run-tests --app billing

# Build the dashboard SPA
cd apps/billing/dashboard && yarn build
```

Next: [07 — Glossary](07-glossary.md).
