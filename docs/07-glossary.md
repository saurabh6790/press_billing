# 07 — Glossary

The precise language of the domain. When two words could mean the same thing, the
**_Avoid_** note says which to drop. (Condensed from the project's `CONTEXT.md`.)

## Catalog

**Bundle** — a flat-rate sellable offering of bundled resources (e.g. 2 vCPU +
4 GB + 80 GB). Has **one immutable identity forever** (`bundle-2vcpu`); a price
change never forks a new one. Modelled as the **Plan** DocType.
_Avoid_: plan version, tier, SKU.

**Add-on** — a per-unit resource billed on top of a bundle (snapshot, transfer
overage, extra disk, IP). It is `rate × quantity`. Either **grandfathered** (rate
locked at provision) or **live-priced**, set per add-on type.
_Avoid_: extra, upsell, supplement.

**Live-priced add-on** — an add-on whose rate is read from the *current* Catalog
Rate each billing period rather than locked at provision — the deliberate
exception to grandfathering. Used for depreciating storage (snapshots), so a
customer is never stranded on a stale-high rate.
_Avoid_: spot price, current price.

**Rate** — the single pricing word. For a **bundle**, the rate *is* the price
(never `quantity × rate`). For an **add-on**, it is the per-unit price. A rate
change is a new **Catalog Rate** document, never a new bundle.
_Avoid_: price, price_per_unit, cost, tariff.

**Composition** (a bundle's *includes*) — the resources a bundle contains
(compute / memory / disk), recorded as spec only — **no price**. Also the
**allowance** baseline that add-on overage is measured against.
_Avoid_: line items, priced parts.

**Catalog Rate** — one standalone DocType (ERPNext *Item Price* style) holding
every bundle's and add-on's rate, one row per `(priced_for, cluster, currency)`.
A new currency or region is a new Catalog Rate *document*, never a new column.

## Money

**Minor unit** — the smallest indivisible amount of a currency (**paisa** for INR,
**cent** for USD). All settled money is a **64-bit integer count of minor units** —
never a float, never a `Currency` field. Display = integer ÷ the currency's factor
(100 for INR/USD, 1 for JPY, 1000 for BHD — read from the **Currency** DocType).
₹10.00 is `1000`, not `10.0`.
_Avoid_: float rupees, `Currency` field, "amount in rupees".

**Rate unit** — the sub-minor scale a **per-unit rate** is stored at: minor units
× 10⁶, so a sub-paisa metered rate is representable (€0.009/GB → `900000` rate
units). Held as `Long Int`. Rounding from rate units to settled minor units
happens **once per line item** (half away from zero).
_Avoid_: storing per-unit rates in plain paisa.

See ADR 0003 — money as integer minor units.

## Pricing in time

**Commitment** — a team-level promise to keep monthly spend at or above a
**floor** for a fixed **term**, in exchange for a discounted rate on each
monthly-in-arrears invoice. **Resource-agnostic** — upgrade/downgrade/swap freely
while committed spend stays at/above the floor.
_Avoid_: contract, lock-in, reservation.

**Floor** — the minimum monthly **fixed bundle spend** a Commitment guarantees.
Metered usage and one-off add-ons bill at list, never count toward the floor, and
never get the commitment discount.
_Avoid_: minimum, quota, cap (a cap is a ceiling — a floor is the opposite).

**Clawback** — the reconciling charge when a team drops committed spend **below
the floor** before term-end: it repays the discount enjoyed on months already
consumed. Never a fee for unrendered service.
_Avoid_: penalty, termination fee.

**Price-lock** — the append-only record, keyed by **resource_id**, that freezes
the rate (and allowance) a specific provisioned resource was shown at provision.
Billing reads it forever; this is how grandfathering works. Re-provisioning yields
a new resource_id and a new lock.
_Avoid_: grandfather record, price history, snapshot (overloaded).

**Shown rate** — the live rate resolved for the customer's currency + cluster at
purchase and displayed in the UI. The Agent reports it on the `subscribed` event
so **rate shown = rate locked**.

## Resource lifecycle (billing view)

**Alive** — a provisioned resource that is **running or stopped**. Both bill the
full bundle rate — a stopped resource still reserves its compute, so stopping does
**not** reduce the bill (DigitalOcean model, not AWS).
_Avoid_: active, on.

**Terminated** — a resource that has been destroyed. Compute billing stops (the
price-lock closes); only retained **snapshots** keep billing, at the **live**
snapshot rate (a snapshot is its own resource_id from birth).
_Avoid_: deleted, cancelled, off.

## State axes (never one enum)

**Operational state** (Agent) — `running` / `stopped` / `terminated`.

**Account standing** (Central, `Subscription.account_standing`) — `current` /
`past_due` / `suspended`.

## Two apps

**Central** — the `billing` app (this repo). Sole system of record for money and
the customer's monetary standing. The only component that talks to gateways.

**Subscription Agent** — the per-cluster `press_billing_agent` app. Authoritative
for **what actually ran**. Records the immutable event log + usage rollups,
enforces entitlement tokens offline, syncs to Central. No financial logic.
