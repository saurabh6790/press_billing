# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Demo scenarios — one team per state, so every flow can be shown (#demo).

    bench --site billing.local execute press_billing.demo_scenarios.seed_all

Builds the happy-path `demo` team (press_billing.demo.seed) plus a team for each
scenario: overdue/dunning, suspended, trial cost_report, credits-only,
refund, SEZ zero-rating, TDS withholding, reconciliation, and a Razorpay UPI
mandate. Authentic records throughout — flows that need a live gateway have their
end-state constructed directly (no test credentials required).
"""

import frappe

from press_billing import billing, credits, demo, notifications, subscriptions
from press_billing.sync import receive_usage_events

CLUSTER = demo.CLUSTER
PLAN = demo.PLAN
STRIPE_GW = demo.GATEWAY
RAZORPAY_GW = "GW-Demo-Razorpay"
PAYPAL_GW = "GW-Demo-PayPal"


def seed_all() -> dict:
	demo.seed()  # happy-path `demo` team + catalog + gateways + tier levels + workspace
	_extra_gateways()
	_ensure_signing_key()

	results = {"demo": "happy path (Paid May + Open June, wallet, card)"}
	results["demo-overdue"] = scenario_overdue()
	results["demo-suspended"] = scenario_suspended()
	results["demo-trial"] = scenario_trial()
	results["demo-credits"] = scenario_credits_only()
	results["demo-refund"] = scenario_refund()
	results["demo-sez"] = scenario_sez()
	results["demo-tds"] = scenario_tds()
	results["demo-recon"] = scenario_reconciliation()
	results["demo-razorpay"] = scenario_razorpay_mandate()
	frappe.db.commit()
	return results


# --- scenarios --------------------------------------------------------------


def scenario_overdue() -> str:
	"""A billable team in dunning: Overdue invoice, standing past_due, 3 failed
	retries, still running (grace)."""
	team = "demo-overdue"
	_base(team, tier="t1", gst=True)
	card = _card(team, STRIPE_GW)
	sub = _subscription(team, card, STRIPE_GW)
	_provision(team, "srv-od-1", 3200)
	inv = billing.generate_draft_invoice(sub, "2026-06-01", "2026-06-30")
	frappe.db.set_value("Invoice", inv, {"status": "Overdue", "due_date": "2026-06-01", "amount_paid": 0})
	subscriptions.set_standing(sub, "past_due", changed_by="dunning")
	for n in range(3):
		_failed_attempt(team, inv, card, STRIPE_GW, retry=n)
		notifications.notify(team, "payment_retry",
			message=f"Payment retry {n + 1} for invoice {inv} failed: card_declined",
			reference_doctype="Invoice", reference_name=inv)
	notifications.notify(team, "invoice_overdue", context={"invoice": inv},
		reference_doctype="Invoice", reference_name=inv)
	return "Overdue invoice + past_due + 3 failed retries"


def scenario_suspended() -> str:
	"""Dunning escalated: standing suspended + a cap-0 suspend directive token."""
	team = "demo-suspended"
	_base(team, tier="t1", gst=True)
	card = _card(team, STRIPE_GW)
	sub = _subscription(team, card, STRIPE_GW)
	_provision(team, "srv-su-1", 3200)
	inv = billing.generate_draft_invoice(sub, "2026-06-01", "2026-06-30")
	frappe.db.set_value("Invoice", inv, {"status": "Overdue", "due_date": "2026-05-20", "amount_paid": 0})
	subscriptions.set_standing(sub, "past_due", changed_by="dunning")
	subscriptions.set_standing(sub, "suspended", changed_by="dunning")
	from press_billing.entitlements import issue_token

	issue_token(team, {}, suspend=True)
	notifications.notify(team, "invoice_overdue", context={"invoice": inv},
		reference_doctype="Invoice", reference_name=inv)
	return "Suspended + cap-0 suspend token on the entitlement channel"


def scenario_trial() -> str:
	"""Free/trial = entry tier → invoice_type cost_report (computed, not charged)."""
	team = "demo-trial"
	_base(team, tier="t0", gst=False)  # entry tier
	sub = _subscription(team)
	_provision(team, "srv-tr-1", 3200)
	inv = billing.generate_draft_invoice(sub, "2026-06-01", "2026-06-30")
	billing.open_and_collect(inv)  # cost_report → opened, never charged
	return "cost_report invoice (trial subsidy)"


def scenario_credits_only() -> str:
	"""Credits-only team: credits applied first, remainder left Open (no card)."""
	team = "demo-credits"
	_base(team, tier="t1", gst=True)
	sub = _subscription(team)  # no card / gateway
	_provision(team, "srv-cr-1", 3200)
	credits.purchase(team, 2000, "INR", note="Demo top-up")
	inv = billing.generate_draft_invoice(sub, "2026-06-01", "2026-06-30")
	billing.open_and_collect(inv)  # credits-first; remainder stays Open for dunning
	return "credits applied + Open remainder; wallet-gated"


def scenario_refund() -> str:
	"""A Paid invoice with a full dispute (to source) and a partial overcharge
	(to wallet)."""
	team = "demo-refund"
	_base(team, tier="t1", gst=True)
	card = _card(team, STRIPE_GW)
	sub = _subscription(team, card, STRIPE_GW)
	_provision(team, "srv-rf-1", 3200)
	inv = billing.generate_draft_invoice(sub, "2026-06-01", "2026-06-30")
	total = frappe.db.get_value("Invoice", inv, "total")
	frappe.db.set_value("Invoice", inv, {"status": "Paid", "amount_paid": total, "due_date": "2026-07-07"})
	attempt = frappe.get_doc({
		"doctype": "Payment Attempt", "invoice": inv, "team": team, "gateway": STRIPE_GW,
		"payment_method": card, "amount": total, "currency": "INR", "status": "captured",
		"gateway_transaction_id": "pi_demo_refund", "resolved_by": "webhook",
	}).insert(ignore_permissions=True).name
	# Full dispute → source (invoice stays Paid).
	frappe.get_doc({
		"doctype": "Refund", "payment_attempt": attempt, "invoice": inv, "team": team,
		"amount": total, "currency": "INR", "destination": "source", "status": "completed",
		"gateway_refund_id": "re_demo_full", "reason": "Full dispute",
		"created_at": frappe.utils.now_datetime(), "completed_at": frappe.utils.now_datetime(),
	}).insert(ignore_permissions=True)
	# Partial overcharge → wallet credit (applied next cycle).
	wallet = credits.refund_to_wallet(team, 200, currency="INR", reference_type="Refund",
		reference_name="demo-partial", note="Partial overcharge")
	frappe.get_doc({
		"doctype": "Refund", "payment_attempt": attempt, "invoice": inv, "team": team,
		"amount": 200, "currency": "INR", "destination": "wallet", "status": "completed",
		"reason": "Partial overcharge", "created_at": frappe.utils.now_datetime(),
		"completed_at": frappe.utils.now_datetime(),
	}).insert(ignore_permissions=True)
	return f"full refund→source + partial→wallet (balance {wallet['new_balance']})"


def scenario_sez() -> str:
	"""SEZ/export: zero-rated output tax WITH a compliance reason."""
	team = "demo-sez"
	_base(team, tier="t1", gst=False)
	demo._replace("Tax Profile", team, {"output_tax_type": "GST", "output_tax_rate": 18,
		"zero_rated": 1, "zero_rating_reason": "sez_lut"})
	sub = _subscription(team)
	_provision(team, "srv-sez-1", 3200)
	inv = billing.generate_draft_invoice(sub, "2026-06-01", "2026-06-30")
	frappe.db.set_value("Invoice", inv, {"status": "Open", "due_date": "2026-07-07"})
	return "zero-rated (sez_lut) — tax 0 with reason"


def scenario_tds() -> str:
	"""TDS withholding: total unchanged, expected_collection reduced."""
	team = "demo-tds"
	_base(team, tier="t1", gst=False)
	demo._replace("Tax Profile", team, {"output_tax_type": "GST", "output_tax_rate": 18,
		"tds_applicable": 1, "tds_rate": 10})
	sub = _subscription(team)
	_provision(team, "srv-tds-1", 3200)
	inv = billing.generate_draft_invoice(sub, "2026-06-01", "2026-06-30")
	frappe.db.set_value("Invoice", inv, {"status": "Open", "due_date": "2026-07-07"})
	return "TDS withheld — expected_collection < total"


def scenario_reconciliation() -> str:
	"""An ambiguous (charged-but-never-webhooked) attempt awaiting the recon job."""
	team = "demo-recon"
	_base(team, tier="t1", gst=True)
	card = _card(team, STRIPE_GW)
	sub = _subscription(team, card, STRIPE_GW)
	_provision(team, "srv-rc-1", 3200)
	inv = billing.generate_draft_invoice(sub, "2026-06-01", "2026-06-30")
	frappe.db.set_value("Invoice", inv, {"status": "Open", "due_date": "2026-07-07"})
	attempt = frappe.get_doc({
		"doctype": "Payment Attempt", "invoice": inv, "team": team, "gateway": STRIPE_GW,
		"payment_method": card, "amount": frappe.db.get_value("Invoice", inv, "expected_collection"),
		"currency": "INR", "status": "initiated", "gateway_transaction_id": "pi_stuck_demo",
	}).insert(ignore_permissions=True).name
	frappe.db.set_value("Payment Attempt", attempt,
		"initiated_at", frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=-2))
	return "ambiguous attempt (initiated, no webhook) for reconciliation"


def scenario_razorpay_mandate() -> str:
	"""A Razorpay team with an active UPI Autopay mandate (ceiling = tier cap)."""
	team = "demo-razorpay"
	_base(team, tier="t1", gst=True)
	mandate = frappe.get_doc({
		"doctype": "Payment Method", "team": team, "gateway": RAZORPAY_GW,
		"method_type": "upi_autopay", "status": "active", "display_label": "UPI Autopay",
		"gateway_method_id": "token_demo", "gateway_customer_id": "cust_demo",
		"mandate_max_amount": 50000, "mandate_currency": "INR", "is_default": 1,
		"validated_at": frappe.utils.now_datetime(),
	}).insert(ignore_permissions=True).name
	sub = _subscription(team, mandate, RAZORPAY_GW)
	_provision(team, "srv-rz-1", 3200)
	inv = billing.generate_draft_invoice(sub, "2026-06-01", "2026-06-30")
	frappe.db.set_value("Invoice", inv, {"status": "Open", "due_date": "2026-07-07"})
	return "Razorpay UPI Autopay mandate (cap = tier ceiling)"


# --- helpers ----------------------------------------------------------------


def _base(team, tier, gst):
	_wipe_team(team)
	demo._replace("Trust Tier", team, {"tier": tier, "level": tier,
		"max_spend": 50000 if tier == "t1" else 10000, "manual_override": 1})
	if gst:
		demo._replace("Tax Profile", team, {"output_tax_type": "GST", "output_tax_rate": 18})


def _subscription(team, default_pm=None, gateway=None):
	return subscriptions.create_subscription(
		team=team, cluster=CLUSTER, plan=PLAN, billing_cycle="monthly",
		default_payment_method=default_pm, gateway=gateway).name


def _provision(team, resource, rate, start="2026-06-01 00:00:00"):
	receive_usage_events([{
		"event_id": f"ev-{team}-{resource}", "team": team, "resource_id": resource,
		"cluster": CLUSTER, "plan": PLAN, "shown_rate": rate, "currency": "INR",
		"event_type": "subscribed", "effective_from": start, "effective_to": None,
	}])


def _card(team, gateway, label="Visa ····4242"):
	return frappe.get_doc({
		"doctype": "Payment Method", "team": team, "gateway": gateway, "method_type": "card",
		"status": "active", "display_label": label, "gateway_method_id": f"pm_{team}",
		"gateway_customer_id": f"cus_{team}", "expiry_month": 11, "expiry_year": 2030,
		"is_default": 1, "validated_at": frappe.utils.now_datetime(),
	}).insert(ignore_permissions=True).name


def _failed_attempt(team, invoice, card, gateway, retry):
	frappe.get_doc({
		"doctype": "Payment Attempt", "invoice": invoice, "team": team, "gateway": gateway,
		"payment_method": card, "amount": frappe.db.get_value("Invoice", invoice, "expected_collection"),
		"currency": "INR", "status": "failed", "failure_code": "card_declined",
		"failure_reason": "Your card was declined.", "retry_number": retry,
		"completed_at": frappe.utils.now_datetime(),
	}).insert(ignore_permissions=True)


def _extra_gateways():
	demo._replace("Payment Gateway", RAZORPAY_GW, {"title": "Razorpay (Demo)",
		"adapter_key": "razorpay", "currency": "INR", "api_key": "rzp_test", "api_secret": "rzp_secret",
		"webhook_secret": "rzp_whsec", "is_enabled": 1, "supports_mandates": 1})
	demo._replace("Payment Gateway", PAYPAL_GW, {"title": "PayPal (Demo)",
		"adapter_key": "paypal", "currency": "USD", "api_key": "pp_client", "api_secret": "pp_secret",
		"webhook_secret": "WH-DEMO", "is_enabled": 1})


def _ensure_signing_key():
	if frappe.conf.get("entitlement_private_key"):
		return
	from press_billing.signing import generate_keypair

	priv, pub = generate_keypair()
	frappe.conf.entitlement_private_key = priv
	try:
		frappe.installer.update_site_config("entitlement_private_key", priv)
		frappe.installer.update_site_config("entitlement_public_key", pub)
	except Exception:  # noqa: BLE001 — in-memory conf is enough for the seed run
		pass


def _wipe_team(team):
	for sub in frappe.get_all("Subscription", {"team": team}, pluck="name"):
		frappe.db.delete("Subscription Change", {"subscription": sub})
	for dt in ("Invoice", "Payment Attempt", "Refund", "Payment Method", "Price Lock",
			   "Usage Rollup", "Credit Ledger Entry", "Subscription", "Notification Log",
			   "Entitlement Token"):
		frappe.db.delete(dt, {"team": team})
	for dt in ("Credit Wallet", "Trust Tier", "Tax Profile"):
		if frappe.db.exists(dt, team):
			frappe.delete_doc(dt, team, force=True)
