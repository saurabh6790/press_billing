# 05 — Workflows

The end-to-end lifecycles, each backed by tests. Read these to understand *how
the pieces move together*. State names are the real DocType values.

---

## A. Subscription & the two-axis state

A customer *requests* a plan (intent, on Central). The cluster *provisions*
against a signed entitlement token. Two **orthogonal** state axes are tracked —
never collapse them into one enum.

| Axis | Owner | Values |
|---|---|---|
| **Operational** | Agent | `running` · `stopped` · `terminated` |
| **Account standing** | Central (`Subscription.account_standing`) | `current` · `past_due` · `suspended` |

```mermaid
sequenceDiagram
    actor Cust as Customer
    participant C as Central (Subscription)
    participant E as Entitlement Token
    participant A as Agent (cluster)
    Cust->>C: Subscribe to plan X in region R (intent)
    C->>C: Check trust-tier cap
    C->>E: Issue signed (Ed25519) token, cap = tier
    E-->>A: Push token
    A->>A: Verify token offline, provision resource
    A-->>C: subscribed event (resource_id, shown_rate)
    C->>C: Write Price Lock (rate frozen forever)
```

Key points:

- **Provisioning is regional and Central-independent** — the Agent verifies the
  token offline, so a Central outage never blocks (or stops) a resource.
- On the `subscribed` event the Agent reports the `shown_rate`, so **rate shown =
  rate locked**, guaranteed.
- `stopped` is an *operational* state only — a stopped machine is still **alive**
  and bills the full bundle rate. Only `terminated` stops compute billing.

---

## B. Grandfathering (Price-Lock)

```mermaid
flowchart LR
    Prov[Provision resource] -->|shown_rate| Lock[(Price Lock<br/>append-only, keyed by resource_id)]
    Catalog[Catalog Rate rises] -.->|does NOT touch| Lock
    Lock -->|billing reads forever| Inv[Invoice]
    Catalog -->|only affects| NewProv[New provisions]
```

The **Price Lock** freezes the rate (and allowance) a specific `resource_id` was
shown at provision. Billing reads it forever — raising a Catalog Rate only affects
*new* provisions. Re-provisioning yields a new `resource_id` and a new lock.
(`acme-corp` demo: locked ₹9,360 vs ₹12,000 catalog → `discrepancy = 1`.)

The deliberate exception: **live-priced add-ons** (depreciating storage like
snapshots) read the *current* Catalog Rate each period, so the customer is never
stranded on a stale-high rate.

---

## C. Metering → usage rollup

```mermaid
flowchart LR
    Res[Resource] -->|counter/gauge| AM[Agent: edge aggregation]
    AM -->|usage push| Roll[(Central: Usage Rollup)]
    Roll -->|max 0, qty − allowance × rate| Line[Metered line item]
```

Usage is **edge-aggregated on the Agent** (counters and gauges), so Central stores
bounded rollups, not 10M rows/day. A metered line bills
`max(0, quantity − allowance) × rate` — the allowance comes from the plan's
composition. Receive endpoints: `platform/sync.py:receive_usage_events` /
`receive_meter_rollups`.

---

## D. Two-phase invoicing

Postpaid: everything bills on the 1st for the month just ended. Generation is
split in two so the 1st is never a single blocking loop.

```mermaid
flowchart LR
    subgraph Phase1["28th — Draft"]
        D[Build Draft invoice<br/>from event log × locked price]
    end
    subgraph Phase2["1st — Open"]
        O[Finalise → Open<br/>parallel, no double-processing]
    end
    D --> O --> Charge[Trigger settlement]
```

Invoice state machine:

```mermaid
stateDiagram-v2
    [*] --> Draft: 28th, computed
    Draft --> Open: 1st, finalised
    Open --> Paid: webhook-confirmed
    Open --> Overdue: dunning window elapsed
    Overdue --> Paid: retry succeeds
    Open --> Waived: admin
    Draft --> Cancelled: correction
    Paid --> [*]
```

- An invoice is **computed** from line items (`revenue/invoicing/lines.py`), never
  a stored "amount".
- `invoice_type` is `billable` normally, or `cost_report` for trials (computed,
  not charged).
- Each region a team occupies gets **one invoice per region per month** (multiple
  day-weighted line items).

---

## E. Settlement — credits-then-card waterfall

When an invoice opens, Central settles it. Credits apply first; the remainder
goes to the card.

```mermaid
flowchart TB
    Open[Invoice Open] --> Credits{Wallet balance?}
    Credits -->|covers total| PaidC[Apply credits → Paid]
    Credits -->|partial / none| Remainder[Charge remainder to card]
    Remainder --> Attempt[Payment Attempt]
    Attempt --> GW[Gateway charge]
    GW --> WH{Webhook}
    WH -->|captured| Paid[Invoice → Paid]
    WH -->|failed| Dun[Enter dunning]
```

- **Credits-only teams** (prepaid mode) are gated by `min(tier cap, wallet)`.
- A **credit shortfall** (wallet can't cover the month's projection) raises an
  alert (demo: `hooli`). The 80% forecast threshold drives early warning.
- Settlement source is gated by mode (postpaid → card, prepaid → credits).
  Code: `payments/settlement.py`.

---

## F. Charge → Payment Attempt → webhook → Paid

The only path to `Paid` is a **verified webhook**. The receiver is
**signature-first**: it verifies the gateway HMAC *before* any DB access.

```mermaid
sequenceDiagram
    participant C as Central (charges.py)
    participant G as Gateway adapter
    participant GW as Gateway
    participant W as webhooks.py
    C->>C: Create Payment Attempt (status=initiated)
    C->>G: charge(idempotency_key = attempt.name)
    G->>GW: API call
    GW-->>C: authorised/captured (sync)
    GW-->>W: webhook (gateway_event_id)
    W->>W: 1. Verify HMAC signature (FIRST)
    W->>W: 2. Dedupe on gateway_event_id
    W->>W: 3. Mark attempt captured, Invoice → Paid (resolved_by=webhook)
```

- **Idempotency**: the charge carries an idempotency key derived from
  `payment_attempt.name`; webhooks dedupe on `gateway_event_id` (a concurrent
  flood stores exactly one).
- `Payment Attempt.status`: `initiated → authorised → captured → failed →
  refunded`. `resolved_by` records provenance: `webhook` or `reconciliation`.

### Payment-method fallback

If the primary method fails, collection walks the team's methods in priority
order (`payments/collection.py`) — **escalate, don't repeat** the same method; a
duplicate card is deduped.

---

## G. Dunning → suspend → terminate

The daily `run_dunning` job walks unpaid invoices through a staged ladder. The
suspend directive travels on the **entitlement-token channel** — Central being
unreachable never stops a resource; only an explicit cap-0 suspend token does.

```mermaid
flowchart LR
    Open[Invoice Open] --> D1[Day 1 retry]
    D1 -->|fail| D3[Day 3 retry]
    D3 -->|fail| D7[Day 7 retry]
    D7 -->|fail| OD[Overdue / past_due<br/>still running]
    OD --> D14[Day 14: suspend directive<br/>cap-0 token to Agent]
    D14 --> Susp[Agent stops resource<br/>account_standing = suspended]
    Susp --> Term[Terminate]
    D1 -->|success| Paid[Paid]
    D3 -->|success| Paid
    D7 -->|success| Paid
```

Critical distinction (demo `stark-ind` vs `cyberdyne`): a team in `past_due` keeps
**running**; an *expired* token never stops a customer's resources. Only a
**suspend token** (cap 0) makes the Agent stop them.

---

## H. Refunds

Two shapes, by intent (`payments/refunds.py`, `Refund.destination`):

```mermaid
flowchart TB
    R{Refund reason} -->|full dispute| Src[destination = source<br/>refund to gateway<br/>invoice STAYS Paid]
    R -->|partial overcharge| Wallet[destination = wallet<br/>credit applied next cycle]
    R -->|pre-payment correction| Reissue[Cancel + reissue invoice]
```

A full dispute refunds to the original **source** and the invoice stays `Paid`
(money moved, the bill was still valid). A partial overcharge becomes a **wallet
credit** (demo `soylent`). A correction *before* payment is a cancel + reissue.

---

## I. Reconciliation

The daily `run_reconciliation` job is a **read-only** scan for charges that
succeeded at the gateway but whose webhook never arrived.

```mermaid
flowchart LR
    Scan[Daily scan] --> Find[Find charged-but-not-Paid attempts]
    Find --> GWq[Query gateway truth read-only]
    GWq -->|captured at gateway| Fix[Mark Paid<br/>resolved_by = reconciliation]
    GWq -->|not captured| Leave[Leave for dunning]
```

It is idempotent (no double charge) and records `resolved_by = reconciliation` so
the provenance of every `Paid` is auditable. Human-in-the-loop decisions are
recorded too.

---

## J. Trials (trial = entry tier)

A trial is simply the **entry trust tier**. Its invoices are
`invoice_type = cost_report` — **computed, not charged** — so you can see what a
team *would* owe (and the subsidy). Converting flips invoices to `billable` with
resources untouched (`catalog/trials.py`). Demo: `piedpiper`.

---

## K. ERPNext sync (async, one-way)

After an invoice is `Paid`, Central enqueues a one-way **Sales Invoice** push to
ERPNext (the statutory accounting SOR). It uses exponential-backoff retries
(hourly `retry_failed_syncs`) and is **failure-isolated**: a sync failure never
rolls back the customer invoice. `erpnext_sync_status`: `pending → synced →
failed`.

---

Next: [06 — Actions & API reference](06-actions.md).
