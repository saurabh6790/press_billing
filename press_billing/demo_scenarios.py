# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Comprehensive demo dataset for the billing portal (#demo).

    bench --site billing.local execute press_billing.demo_scenarios.seed_all

Wipes ALL press_billing data, then builds a realistic multi-region catalog and
ten teams so every dashboard criterion can be demonstrated:

* 3 clusters — India (Mumbai), Europe (Frankfurt), Middle East (Dubai).
* 5 plan sizes (1→16 vCPU), each priced per cluster x currency (INR/EUR/USD),
  so a team paying in one currency can subscribe to any region.
* 4 trust tiers (t0 trial → t3 enterprise). Higher-tier teams carry ~10 months
  of paid invoices; lower tiers a month or two.
* Mixed currencies, including INR-paying teams running in EU / Middle East.
* A grandfathering example: a long-standing team billed at its locked launch
  rate while the catalog price has since risen (price-lock discrepancy).
* Per-team states: active, overdue/dunning, suspended, prepaid credits, refund,
  and a free-trial cost report.

The Agent-side mirror lives in press_billing_agent.demo.seed.
"""

import frappe

from press_billing import billing, credits, notifications, subscriptions
from press_billing.pricing import set_catalog_rates
from press_billing.sync import receive_meter_rollups, receive_usage_events

# --- catalog shape ----------------------------------------------------------

# (slug, label, billing currency of the region)
CLUSTERS = [
	("in-mumbai", "India — Mumbai", "INR"),
	("eu-frankfurt", "Europe — Frankfurt", "EUR"),
	("me-dubai", "Middle East — Dubai", "USD"),
]
CURRENCIES = ["INR", "EUR", "USD"]
# 1 unit of currency = N INR (rough FX, demo only).
FX = {"INR": 1.0, "EUR": 90.0, "USD": 83.0}
# Regional cost multiplier on the INR base price.
CLUSTER_MULT = {"in-mumbai": 1.0, "eu-frankfurt": 1.25, "me-dubai": 1.15}

# (slug, title, vcpu, ram_gb, disk_gb, transfer_gb_included, base_inr_monthly)
PLAN_SIZES = [
	("plan-1vcpu", "Starter · 1 vCPU / 2 GB", 1, 2, 25, 100, 1500),
	("plan-2vcpu", "Basic · 2 vCPU / 4 GB", 2, 4, 50, 200, 3000),
	("plan-4vcpu", "Standard · 4 vCPU / 8 GB", 4, 8, 100, 400, 6000),
	("plan-8vcpu", "Pro · 8 vCPU / 16 GB", 8, 16, 200, 800, 12000),
	("plan-16vcpu", "Enterprise · 16 vCPU / 32 GB", 16, 32, 400, 1600, 24000),
]

# Metered bandwidth overage, priced per GB per currency (cluster-agnostic).
ADDON = "addon-transfer"
ADDON_RATE = {"INR": 0.80, "EUR": 0.009, "USD": 0.010}

# (level, sequence, is_default, max_spend_inr, max_resources, min_invoices, min_paid_inr)
TIERS = [
	("t0", 0, 1, 5000, 3, 0, 0),
	("t1", 1, 0, 50000, 25, 1, 3000),
	("t2", 2, 0, 200000, 100, 6, 50000),
	("t3", 3, 0, 1000000, 500, 10, 500000),
]

# Output tax follows the customer's billing currency (place of supply).
TAX_BY_CURRENCY = {"INR": ("GST", 18), "EUR": ("VAT", 19), "USD": ("VAT", 5)}

# (team, tier, currency, paid_months, state, resources)
#   paid_months = closed Paid invoices per cluster before the current (June) month.
#   resources   = the team's running instances [(cluster, plan), ...] — droplet-
#                 style: any plan in any region, capped by the tier. A team bills
#                 in ONE currency regardless of where its instances run.
TEAMS = [
	("acme-corp", "t3", "INR", 9, "grandfathered", [
		("in-mumbai", "plan-8vcpu"), ("in-mumbai", "plan-2vcpu"),
		("eu-frankfurt", "plan-4vcpu"), ("me-dubai", "plan-1vcpu")]),
	("globex", "t3", "EUR", 9, "active", [
		("eu-frankfurt", "plan-16vcpu"), ("eu-frankfurt", "plan-4vcpu"),
		("in-mumbai", "plan-2vcpu")]),
	("initech", "t2", "USD", 5, "active", [
		("me-dubai", "plan-4vcpu"), ("me-dubai", "plan-1vcpu"), ("eu-frankfurt", "plan-2vcpu")]),
	("umbrella", "t2", "INR", 5, "active", [            # INR billing, EU + India
		("eu-frankfurt", "plan-4vcpu"), ("in-mumbai", "plan-2vcpu")]),
	("wayne-ent", "t2", "INR", 5, "active", [           # INR billing, ME + India
		("me-dubai", "plan-2vcpu"), ("in-mumbai", "plan-1vcpu")]),
	("stark-ind", "t1", "INR", 1, "overdue", [("in-mumbai", "plan-2vcpu")]),
	("cyberdyne", "t1", "EUR", 1, "suspended", [("eu-frankfurt", "plan-2vcpu")]),
	("hooli", "t1", "INR", 1, "credits", [("in-mumbai", "plan-1vcpu")]),
	("soylent", "t1", "USD", 1, "refund", [("me-dubai", "plan-2vcpu")]),
	("piedpiper", "t0", "INR", 0, "trial", [("in-mumbai", "plan-1vcpu")]),
]

STRIPE = {"INR": "GW-Stripe-INR", "EUR": "GW-Stripe-EUR", "USD": "GW-Stripe-USD"}
RAZORPAY = "GW-Razorpay"
ANCHOR = "2026-06-01"  # the current (open) billing month


def seed_all() -> dict:
	from press_billing.dashboard import ensure_billing_team_field

	_wipe_all()
	ensure_billing_team_field()
	_tiers()
	_catalog()
	_gateways()
	_ensure_signing_key()

	results = {}
	for team, tier, currency, months, state, resources in TEAMS:
		results[team] = _build_team(team, tier, currency, months, state, resources)

	from press_billing.demo import _ensure_workspace

	_ensure_workspace()
	# So an admin browsing the portal lands on a rich team by default.
	frappe.db.set_value("User", "Administrator", "billing_team", "acme-corp")
	frappe.db.commit()
	return results


# --- per-team build ---------------------------------------------------------


def _build_team(team, tier, currency, months, state, resources):
	from collections import OrderedDict

	_tier(team, tier)
	_tax(team, currency)
	_profile(team, currency, resources[0][0], prepaid=(state == "credits"))
	gateway, pm = _payment_setup(team, currency, state)

	periods = _month_periods(months)
	first_start = periods[0][0] if periods else ANCHOR

	by_cluster = OrderedDict()
	for cluster, plan in resources:
		by_cluster.setdefault(cluster, []).append(plan)

	# Provision every instance — one price-lock each. The first instance carries
	# the grandfathered (locked launch) rate; the rest lock today's catalog rate.
	idx = 0
	for cluster, plans in by_cluster.items():
		for plan in plans:
			idx += 1
			resource = f"srv-{team}-{idx}"
			catalog = frappe.get_doc("Plan", plan).get_rate(currency, cluster)
			rate = round(catalog * 0.78, 2) if (state == "grandfathered" and idx == 1) else catalog
			receive_usage_events([{
				"event_id": f"ev-{team}-{idx}", "team": team, "resource_id": resource,
				"cluster": cluster, "plan": plan, "shown_rate": rate, "currency": currency,
				"event_type": "subscribed", "effective_from": f"{first_start} 00:00:00", "effective_to": None,
			}])
			# A metered bandwidth overage on the first active instance.
			if idx == 1 and state in ("grandfathered", "active", "credits"):
				allowance = next(p[5] for p in PLAN_SIZES if p[0] == plan)
				receive_meter_rollups([{
					"resource_id": resource, "resource_type": "transfer", "meter_type": "counter",
					"period_start": f"{ANCHOR} 00:00:00", "period_end": "2026-06-30 23:59:59",
					"quantity": round(allowance * 1.25), "unit": "GB",
					"idempotency_key": f"{resource}:counter:{ANCHOR}", "status": "closed",
				}])

	# One subscription per cluster carries the per-region billing intent (and the
	# default payment method that funds the auto-charge). But the customer sees a
	# SINGLE consolidated invoice per month — generate_team_invoice rolls every
	# cluster's day-weighted lines + overage into one Invoice per period.
	subs = []
	for cluster, plans in by_cluster.items():
		subs.append(subscriptions.create_subscription(
			team=team, cluster=cluster, plan=plans[0], billing_cycle="monthly",
			default_payment_method=pm, gateway=gateway,
		).name)
	primary_sub = subs[0]

	for start, end in periods:
		inv = billing.generate_team_invoice(team, start, end, subscription=primary_sub)
		if inv:
			total = frappe.db.get_value("Invoice", inv, "expected_collection")
			frappe.db.set_value("Invoice", inv, {
				"status": "Paid", "amount_paid": total, "due_date": frappe.utils.add_days(end, 7),
			})

	note = _finish_current_month(team, primary_sub, currency, state, pm, gateway)
	return f"{len(resources)} instances across {len(by_cluster)} region(s) — {note}"


def _set_team_standing(team, standing, changed_by="dunning"):
	"""Move every one of the team's subscriptions to a standing (the team — not a
	single region — is past_due/suspended)."""
	for s in frappe.get_all("Subscription", {"team": team}, pluck="name"):
		subscriptions.set_standing(s, standing, changed_by=changed_by)


def _finish_current_month(team, sub, currency, state, pm, gateway):
	"""Build the open/June invoice (one consolidated invoice) in the team's terminal state."""
	if state == "trial":
		inv = billing.generate_team_invoice(team, ANCHOR, "2026-06-30", subscription=sub)
		if inv:
			billing.open_and_collect(inv)  # cost_report → opened, never charged
		return "trial cost report"

	inv = billing.generate_team_invoice(team, ANCHOR, "2026-06-30", subscription=sub)
	if not inv:
		return state

	if state == "overdue":
		frappe.db.set_value("Invoice", inv, {"status": "Overdue", "due_date": "2026-06-01", "amount_paid": 0})
		_set_team_standing(team, "past_due")
		for n in range(3):
			_failed_attempt(team, inv, pm, gateway, n)
			notifications.notify(team, "payment_retry",
				message=f"Payment retry {n + 1} for {inv} failed: card_declined",
				reference_doctype="Invoice", reference_name=inv)
		notifications.notify(team, "invoice_overdue", context={"invoice": inv},
			reference_doctype="Invoice", reference_name=inv)
		return "Overdue + past_due + 3 failed retries"

	if state == "suspended":
		frappe.db.set_value("Invoice", inv, {"status": "Overdue", "due_date": "2026-05-20", "amount_paid": 0})
		_set_team_standing(team, "past_due")
		# Suspension follows EXHAUSTED dunning — the card on file was charged and
		# declined on each retry. Those attempts are non-negotiable history.
		for n in range(3):
			_failed_attempt(team, inv, pm, gateway, n)
			notifications.notify(team, "payment_retry",
				message=f"Payment retry {n + 1} for {inv} failed: card_declined",
				reference_doctype="Invoice", reference_name=inv)
		_set_team_standing(team, "suspended")
		from press_billing.entitlements import issue_token

		issue_token(team, {}, suspend=True)
		notifications.notify(team, "invoice_overdue", context={"invoice": inv},
			reference_doctype="Invoice", reference_name=inv)
		return "Suspended + 3 failed retries + cap-0 suspend token"

	if state == "credits":
		# Deliberately under-fund so the prepaid shortfall + credit alert show.
		credits.purchase(team, 1000, currency, note="Demo top-up")
		billing.open_and_collect(inv)  # credits-first; remainder Open for dunning
		return "prepaid credits applied + Open remainder (shortfall)"

	if state == "refund":
		total = frappe.db.get_value("Invoice", inv, "total")
		frappe.db.set_value("Invoice", inv, {"status": "Paid", "amount_paid": total, "due_date": "2026-07-07"})
		attempt = frappe.get_doc({
			"doctype": "Payment Attempt", "invoice": inv, "team": team, "gateway": gateway,
			"payment_method": pm, "amount": total, "currency": currency, "status": "captured",
			"gateway_transaction_id": f"pi_{team}", "resolved_by": "webhook",
		}).insert(ignore_permissions=True).name
		frappe.get_doc({
			"doctype": "Refund", "payment_attempt": attempt, "invoice": inv, "team": team,
			"amount": round(total * 0.1, 2), "currency": currency, "destination": "wallet",
			"status": "completed", "reason": "Partial overcharge",
			"created_at": frappe.utils.now_datetime(), "completed_at": frappe.utils.now_datetime(),
		}).insert(ignore_permissions=True)
		credits.refund_to_wallet(team, round(total * 0.1, 2), currency=currency,
			reference_type="Refund", reference_name=f"{team}-partial", note="Partial overcharge")
		return "Paid + partial refund → wallet"

	# active / grandfathered
	frappe.db.set_value("Invoice", inv, {"status": "Open", "due_date": "2026-07-07"})
	return "grandfathered (locked launch rate)" if state == "grandfathered" else "active, open current invoice"


# --- catalog / config builders ----------------------------------------------


def _tiers():
	for level, seq, default, cap, res, inv, paid in TIERS:
		_upsert("Trust Tier Level", level, {
			"tier": level, "sequence": seq, "is_default": default,
			"max_spend": cap, "max_resource_count": res,
			"min_paid_invoices": inv, "min_cumulative_paid": paid,
		}, newname=True)


def _catalog():
	for slug, title, vcpu, ram, disk, transfer, base_inr in PLAN_SIZES:
		rates = []
		for cslug, _label, _cur in CLUSTERS:
			for currency in CURRENCIES:
				rate = round(base_inr * CLUSTER_MULT[cslug] / FX[currency], 2)
				rates.append({"cluster": cslug, "currency": currency, "rate": rate})
		plan = _upsert("Plan", slug, {
			"title": title, "billing_cycle": "monthly", "is_active": 1,
			"includes": [
				{"resource_type": "compute", "quantity": vcpu, "unit": "vCPU"},
				{"resource_type": "memory", "quantity": ram, "unit": "GB"},
				{"resource_type": "disk", "quantity": disk, "unit": "GB"},
				{"resource_type": "transfer", "quantity": transfer, "unit": "GB"},
			],
		}, newname=True)
		set_catalog_rates("Plan", plan, rates)

	addon = _upsert("Add-on", ADDON, {
		"title": "Bandwidth Overage", "resource_type": "transfer", "unit": "GB",
		"billing_type": "metered", "billing_interval": "monthly",
	}, newname=True)
	set_catalog_rates(
		"Add-on", addon, [{"cluster": "", "currency": c, "rate": ADDON_RATE[c]} for c in CURRENCIES]
	)


def _gateways():
	for currency, name in STRIPE.items():
		_upsert("Payment Gateway", name, {
			"title": f"Stripe ({currency})", "adapter_key": "stripe", "currency": currency,
			"api_secret": "sk_test_demo", "webhook_secret": "whsec_demo",
			"is_enabled": 1, "is_default_for_currency": 1,
		}, newname=True)
	_upsert("Payment Gateway", RAZORPAY, {
		"title": "Razorpay (India)", "adapter_key": "razorpay", "currency": "INR",
		"api_key": "rzp_test", "api_secret": "rzp_secret", "webhook_secret": "rzp_whsec",
		"is_enabled": 1, "supports_mandates": 1,
	}, newname=True)


def _tier(team, level):
	cap = next(t[3] for t in TIERS if t[0] == level)
	res = next(t[4] for t in TIERS if t[0] == level)
	_upsert("Trust Tier", team, {
		"team": team, "level": level, "tier": level,
		"max_spend": cap, "max_resource_count": res, "manual_override": 1,
	})


def _tax(team, currency):
	tax_type, rate = TAX_BY_CURRENCY[currency]
	_upsert("Tax Profile", team, {"team": team, "output_tax_type": tax_type, "output_tax_rate": rate})


def _profile(team, currency, cluster, prepaid):
	region = next(label for slug, label, _c in CLUSTERS if slug == cluster)
	india = currency == "INR"
	_upsert("Billing Profile", team, {
		"team": team, "legal_name": f"{team.replace('-', ' ').title()} Ltd",
		"email": f"billing@{team}.example",
		"gstin": "27AAPFU0939F1ZV" if india else None,
		"address_line1": "1 Demo Street", "city": region.split("—")[-1].strip(),
		"state": "Maharashtra" if india else "", "country": "India" if india else region.split("—")[0].strip(),
		"pincode": "400001" if india else "",
		"billing_mode": "prepaid" if prepaid else "postpaid",
	})


def _payment_setup(team, currency, state):
	"""Return (gateway, payment_method) for the team's terminal state."""
	if state in ("credits", "trial"):
		return None, None  # prepaid wallet / unpaid trial — no card
	if currency == "INR" and team == "wayne-ent":
		# An INR team on UPI Autopay (mandate ceiling = tier cap).
		pm = frappe.get_doc({
			"doctype": "Payment Method", "team": team, "gateway": RAZORPAY,
			"method_type": "upi_autopay", "status": "active", "display_label": "UPI Autopay",
			"gateway_method_id": f"token_{team}", "gateway_customer_id": f"cust_{team}",
			"mandate_max_amount": 200000, "mandate_currency": "INR", "is_default": 1,
			"validated_at": frappe.utils.now_datetime(),
		}).insert(ignore_permissions=True).name
		return RAZORPAY, pm
	gateway = STRIPE[currency]
	pm = frappe.get_doc({
		"doctype": "Payment Method", "team": team, "gateway": gateway, "method_type": "card",
		"status": "active", "display_label": "Visa ····4242", "gateway_method_id": f"pm_{team}",
		"gateway_customer_id": f"cus_{team}", "expiry_month": 11, "expiry_year": 2030,
		"is_default": 1, "validated_at": frappe.utils.now_datetime(),
	}).insert(ignore_permissions=True).name
	return gateway, pm


def _failed_attempt(team, invoice, pm, gateway, retry):
	frappe.get_doc({
		"doctype": "Payment Attempt", "invoice": invoice, "team": team, "gateway": gateway,
		"payment_method": pm, "amount": frappe.db.get_value("Invoice", invoice, "expected_collection"),
		"currency": frappe.db.get_value("Invoice", invoice, "currency"), "status": "failed",
		"failure_code": "card_declined", "failure_reason": "Your card was declined.",
		"retry_number": retry, "completed_at": frappe.utils.now_datetime(),
	}).insert(ignore_permissions=True)


# --- helpers ----------------------------------------------------------------


def _month_periods(n):
	"""The n closed month windows immediately before ANCHOR, oldest first."""
	anchor = frappe.utils.getdate(ANCHOR)
	out = []
	for i in range(n, 0, -1):
		start = frappe.utils.add_months(anchor, -i)
		out.append((str(start), str(frappe.utils.get_last_day(start))))
	return out


def _upsert(doctype, name, values, newname=False):
	if frappe.db.exists(doctype, name):
		frappe.delete_doc(doctype, name, force=True)
	doc = {"doctype": doctype, **values}
	if newname:
		doc["__newname"] = name
	return frappe.get_doc(doc).insert(ignore_permissions=True).name


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


def _wipe_all():
	"""Drop every press_billing record so the demo is the only data present."""
	children = ("Catalog Rate", "Plan Includes", "Invoice Line Item",
				"Subscription Change")
	transactional = ("Invoice", "Payment Attempt", "Refund", "Payment Method", "Price Lock",
					 "Usage Rollup", "Credit Ledger Entry", "Credit Wallet", "Notification Log",
					 "Entitlement Token", "Webhook Event", "Subscription")
	config = ("Trust Tier", "Tax Profile", "Billing Profile")
	catalog = ("Plan", "Add-on", "Payment Gateway", "Trust Tier Level")
	for dt in children + transactional + config + catalog:
		try:
			frappe.db.delete(dt)
		except Exception:  # noqa: BLE001 — some doctypes may not exist on older sites
			pass
	frappe.db.commit()
