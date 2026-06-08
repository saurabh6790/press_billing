# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Postpaid, in-arrears invoice generation (issue #09).

Two phases, decoupled to avoid the 1st-of-month bottleneck:

  Phase 1 (28th, heavy/off-peak): per active subscription, reconcile sync if
    stale, compute day-weighted line items from the Central price-lock segments
    (event-log time windows x the locked rate, with the max(1, end-start)
    floor), and create a `Draft`.

  Phase 2 (1st, light/parallel): one job per draft applies credits, claims the
    `Draft -> Open` transition atomically (no invoice processed twice), and
    leaves collection to the charge step (#10).

The price-lock ledger already encodes both the time windows (started_at/ended_at
per segment) and the locked rate, so billing reads only Central — no live Agent
call in the common (push-primary) case.
"""

import frappe

from billing import commitments, credits

DEFAULT_DUE_DAYS = 7


# --- line-item engine -------------------------------------------------------


def _days_in_period(period_start, period_end) -> int:
	return (frappe.utils.getdate(period_end) - frappe.utils.getdate(period_start)).days + 1


def compute_line_items(team: str, cluster: str, period_start, period_end) -> list[dict]:
	"""Day-weighted line items for a (team, cluster) over the billing month.

	One line per price-lock run-segment overlapping the period. `ended_at` is
	exclusive — the day of a plan change belongs to the new plan ("new plan wins
	the day"). A segment that opened and closed within a single day still bills
	one day (the max(1,...) floor closes the same-day-churn free faucet). The
	zero-length `cancelled` terminal markers are skipped.
	"""
	period_start = frappe.utils.getdate(period_start)
	period_end = frappe.utils.getdate(period_end)
	period_end_excl = frappe.utils.add_days(period_end, 1)
	units = _days_in_period(period_start, period_end)

	segments = frappe.get_all(
		"Price Lock",
		filters={
			"team": team,
			"cluster": cluster,
			"event_type": ["!=", "cancelled"],
		},
		fields=["name", "resource_id", "plan", "locked_rate", "started_at", "ended_at"],
		order_by="started_at asc",
	)

	lines = []
	for seg in segments:
		seg_start = frappe.utils.getdate(seg.started_at)
		seg_end_excl = frappe.utils.getdate(seg.ended_at) if seg.ended_at else period_end_excl

		# Clamp to the billing period.
		start = max(seg_start, period_start)
		end_excl = min(seg_end_excl, period_end_excl)
		if start >= period_end_excl or end_excl <= period_start:
			continue  # no overlap with this month

		days = max(1, (end_excl - start).days)
		rate = frappe.utils.flt(seg.locked_rate)
		amount = frappe.utils.flt(days * rate / units, 2)
		lines.append(
			{
				"subscription_resource": seg.resource_id,
				"plan": seg.plan,
				"cluster": cluster,
				"resource_type": "bundle",
				"unit": "day",
				"quantity": 1,
				"rate": rate,
				"days": days,
				"amount": amount,
			}
		)
	return lines


# --- phase 1: reconcile-then-draft (28th) -----------------------------------


def reconcile_subscription(subscription_doc):
	"""Pull from the Agent only if the local data is stale.

	Sync is push-primary (#03), so in the common case the event-log segments are
	already on Central and this is a no-op. A real pull would call the Agent's
	get_team_usage; wired here as the seam, exercised by the reconciliation job.
	"""
	return False  # not stale — use what was pushed


def generate_draft_invoice(subscription: str, period_start, period_end):
	"""Reconcile-then-draft one subscription. Idempotent per (subscription, period).

	Returns the (existing or newly created) Draft invoice name, or None when the
	subscription had no billable runtime in the period.
	"""
	sub = frappe.get_doc("Subscription", subscription)
	reconcile_subscription(sub)

	existing = frappe.db.get_value(
		"Invoice",
		{
			"subscription": subscription,
			"period_start": period_start,
			"period_end": period_end,
			"status": ["!=", "Cancelled"],
		},
		"name",
	)
	if existing:
		return existing

	from billing.metering import metered_line_items
	from billing.trials import invoice_type_for

	lines = compute_line_items(sub.team, sub.cluster, period_start, period_end)
	lines += metered_line_items(sub.team, sub.cluster, period_start, period_end)
	if not lines:
		return None

	from billing.tax import resolve_tax

	subtotal = frappe.utils.flt(sum(line["amount"] for line in lines), 2)
	# Commitment (#30 discount / #31 clawback) adjusts the taxable base; subtotal
	# stays gross. Discount reduces it; a breach clawback adds the repaid discount.
	commitment = commitments.resolve_commitment(sub.team, lines, period_start)
	discount = commitment["discount"]
	clawback = commitment["clawback"]
	taxable_base = frappe.utils.flt(subtotal - discount + clawback, 2)
	currency = frappe.db.get_value(
		"Price Lock", {"team": sub.team, "cluster": sub.cluster}, "currency"
	)
	tax = resolve_tax(sub.team, taxable_base)
	total = frappe.utils.flt(taxable_base + tax["output_tax_amount"], 2)
	# expected_collection = total - tds (credits reduce it further at open).
	expected = frappe.utils.flt(total - tax["tds_amount"], 2)

	# The single branch point: an entry-tier (free/trial) team's invoice is a
	# cost_report — computed identically, but a true cost rather than a bill.
	invoice = frappe.get_doc(
		{
			"doctype": "Invoice",
			"team": sub.team,
			"subscription": subscription,
			"invoice_type": invoice_type_for(sub.team),
			"status": "Draft",
			"period_start": period_start,
			"period_end": period_end,
			"currency": currency,
			"items": lines,
			"subtotal": subtotal,
			"commitment_discount": discount,
			"commitment_clawback": clawback,
			"output_tax_type": tax["output_tax_type"],
			"output_tax_rate": tax["output_tax_rate"],
			"output_tax_amount": tax["output_tax_amount"],
			"zero_rating_reason": tax["zero_rating_reason"],
			"tds_applicable": tax["tds_applicable"],
			"tds_rate": tax["tds_rate"],
			"tds_amount": tax["tds_amount"],
			"total": total,
			"credit_applied": 0,
			"expected_collection": expected,
			"amount_paid": 0,
		}
	).insert(ignore_permissions=True)
	commitments.mark_breached(commitment)
	return invoice.name


def generate_team_invoice(team: str, period_start, period_end, subscription: str | None = None):
	"""One consolidated invoice per team per period, across every cluster it runs in.

	A team that runs instances in several regions should see a SINGLE monthly
	invoice, not one per region — so this aggregates the day-weighted fixed lines
	plus metered overage from all of the team's clusters into one Invoice.
	Idempotent per (team, period): a second call returns the existing invoice.

	`subscription` is the primary subscription (its default payment method funds
	the auto-charge in open_and_collect); defaults to any of the team's subs.
	"""
	existing = frappe.db.get_value(
		"Invoice",
		{
			"team": team,
			"period_start": period_start,
			"period_end": period_end,
			"status": ["!=", "Cancelled"],
		},
		"name",
	)
	if existing:
		return existing

	from billing.metering import metered_line_items
	from billing.tax import resolve_tax
	from billing.trials import invoice_type_for

	clusters = sorted(c for c in set(frappe.get_all("Price Lock", {"team": team}, pluck="cluster")) if c)
	lines = []
	for cluster in clusters:
		lines += compute_line_items(team, cluster, period_start, period_end)
		lines += metered_line_items(team, cluster, period_start, period_end)
	if not lines:
		return None

	subtotal = frappe.utils.flt(sum(line["amount"] for line in lines), 2)
	# Commitment (#30 discount / #31 clawback) adjusts the taxable base; subtotal
	# stays gross. Discount reduces it; a breach clawback adds the repaid discount.
	commitment = commitments.resolve_commitment(team, lines, period_start)
	discount = commitment["discount"]
	clawback = commitment["clawback"]
	taxable_base = frappe.utils.flt(subtotal - discount + clawback, 2)
	currency = frappe.db.get_value("Price Lock", {"team": team}, "currency")
	tax = resolve_tax(team, taxable_base)
	total = frappe.utils.flt(taxable_base + tax["output_tax_amount"], 2)
	expected = frappe.utils.flt(total - tax["tds_amount"], 2)
	if subscription is None:
		subscription = frappe.db.get_value("Subscription", {"team": team}, "name")

	invoice = frappe.get_doc(
		{
			"doctype": "Invoice",
			"team": team,
			"subscription": subscription,
			"invoice_type": invoice_type_for(team),
			"status": "Draft",
			"period_start": period_start,
			"period_end": period_end,
			"currency": currency,
			"items": lines,
			"subtotal": subtotal,
			"commitment_discount": discount,
			"commitment_clawback": clawback,
			"output_tax_type": tax["output_tax_type"],
			"output_tax_rate": tax["output_tax_rate"],
			"output_tax_amount": tax["output_tax_amount"],
			"zero_rating_reason": tax["zero_rating_reason"],
			"tds_applicable": tax["tds_applicable"],
			"tds_rate": tax["tds_rate"],
			"tds_amount": tax["tds_amount"],
			"total": total,
			"credit_applied": 0,
			"expected_collection": expected,
			"amount_paid": 0,
		}
	).insert(ignore_permissions=True)
	commitments.mark_breached(commitment)
	return invoice.name


def generate_draft_invoices(period_start, period_end, enqueue: bool = False) -> list[str]:
	"""Phase-1 orchestrator: ONE consolidated draft per team for the period.

	A team that runs instances across several clusters still gets a single
	invoice (generate_team_invoice aggregates all its clusters). The team's first
	subscription is the primary (its payment method funds the auto-charge).
	"""
	primary = {}
	for s in frappe.get_all("Subscription", fields=["name", "team"], order_by="creation asc"):
		primary.setdefault(s.team, s.name)
	created = []
	for team, sub in primary.items():
		if enqueue:
			frappe.enqueue(
				"billing.invoicing.generate_team_invoice",
				team=team,
				period_start=period_start,
				period_end=period_end,
				subscription=sub,
			)
			continue
		name = generate_team_invoice(team, period_start, period_end, subscription=sub)
		if name:
			created.append(name)
	return created


# --- phase 2: open & collect (1st) ------------------------------------------


def open_and_collect(invoice: str, collect: bool = True) -> dict:
	"""Run the credits-then-card waterfall and claim Draft -> Open atomically.

	1. Apply wallet credits first (under the wallet `FOR UPDATE`), reducing the
	   amount due — `credit_applied` recorded on the invoice.
	2. If credits cover the bill in full, the invoice is settled (`Paid`) with no
	   gateway round-trip.
	3. Otherwise open it and charge the **remainder** to the card (#10). A
	   credits-only team with a shortfall is left `Open` for dunning (#14) —
	   never stopped here.

	Concurrency: the invoice row is locked FOR UPDATE and the transition only
	fires from `Draft`, so parallel workers never process the same invoice
	twice — the loser sees a non-Draft status and returns.
	"""
	rows = frappe.db.sql(
		"SELECT status FROM `tabInvoice` WHERE name = %s FOR UPDATE", invoice, as_dict=True
	)
	if not rows or rows[0].status != "Draft":
		return {"invoice": invoice, "claimed": False}

	doc = frappe.get_doc("Invoice", invoice)

	# Free/trial: a cost_report is computed, never collected — no credits, no
	# charge. It is opened as a record of the subsidy cost.
	if doc.invoice_type == "cost_report":
		doc.credit_applied = 0
		doc.expected_collection = 0
		doc.status = "Open"
		doc.save(ignore_permissions=True)
		return {"invoice": invoice, "claimed": True, "cost_report": True, "expected_collection": 0}

	# Leg 1 — credits first (only against the collectable amount, gross less TDS).
	applied = 0
	collectable = frappe.utils.flt(doc.total) - frappe.utils.flt(doc.tds_amount)
	if collectable > 0:
		balance = credits.get_balance(doc.team)["balance"]
		applied = min(frappe.utils.flt(balance), collectable)
		if applied > 0:
			credits.apply_credit(
				doc.team, applied, reference_type="Invoice", reference_name=invoice,
				note=f"Credit applied to {invoice}",
			)

	doc.credit_applied = applied
	# Auto-charge target = gross total, less withheld TDS, less credits applied.
	doc.expected_collection = frappe.utils.flt(
		frappe.utils.flt(doc.total) - frappe.utils.flt(doc.tds_amount) - applied, 2
	)
	doc.due_date = frappe.utils.add_days(frappe.utils.nowdate(), DEFAULT_DUE_DAYS)

	# Credits cover it in full — settled, no card charge needed.
	if doc.expected_collection <= 0:
		doc.status = "Paid"
		doc.save(ignore_permissions=True)
		return {"invoice": invoice, "claimed": True, "credit_applied": applied,
				"expected_collection": 0, "status": "Paid"}

	doc.status = "Open"
	doc.save(ignore_permissions=True)

	# Leg 2 — charge the remainder, walking the team's methods primary→backup
	# (#28). Credits-only teams (no active method) fall through to dunning.
	charge = None
	if collect:
		from billing import collection

		charge = collection.collect_invoice(invoice)

	return {"invoice": invoice, "claimed": True, "credit_applied": applied,
			"expected_collection": doc.expected_collection, "status": "Open", "charge": charge}


def open_drafts(period_end, enqueue: bool = False) -> list[str]:
	"""Phase-2 orchestrator: open every Draft for the billing month."""
	drafts = frappe.get_all(
		"Invoice", filters={"status": "Draft", "period_end": period_end}, pluck="name"
	)
	for inv in drafts:
		if enqueue:
			frappe.enqueue("billing.invoicing.open_and_collect", invoice=inv)
		else:
			open_and_collect(inv)
	return drafts


# --- pre-payment corrections (cancel + reissue) -----------------------------


def cancel_invoice(invoice: str, reason: str | None = None) -> str:
	"""Cancel a pre-payment (Draft/Open/Overdue) invoice.

	Issued line items are never mutated — a correction cancels the whole invoice
	and reissues a fresh one. A Paid invoice cannot be cancelled (use a refund).
	"""
	doc = frappe.get_doc("Invoice", invoice)
	if doc.status == "Paid":
		frappe.throw("A paid invoice cannot be cancelled — issue a refund instead.", frappe.ValidationError)
	if doc.status == "Cancelled":
		return invoice
	doc.status = "Cancelled"
	doc.save(ignore_permissions=True)
	if reason:
		doc.add_comment("Info", f"Cancelled: {reason}")
	return invoice


def reissue_invoice(invoice: str, reason: str | None = None) -> str | None:
	"""Cancel an invoice and regenerate it from current data for the same period.

	The cancelled invoice is excluded from the draft idempotency check, so a new
	Draft is produced. Returns the new invoice name (or None if nothing to bill).
	"""
	doc = frappe.get_doc("Invoice", invoice)
	cancel_invoice(invoice, reason=reason)
	return generate_draft_invoice(doc.subscription, doc.period_start, doc.period_end)
