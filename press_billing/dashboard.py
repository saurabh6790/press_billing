# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Customer dashboard endpoints (issues #26, #18).

Every endpoint is auto-scoped to the caller's team via require_team_access — a
Billing User only ever sees their own team, and passing another team's name is
rejected (never silently widened). Admin-only data (gateway config/secrets,
payment success rates, waive) is never returned here; that lives on the admin
dashboard (#19) behind require_billing_admin.
"""

import frappe

from press_billing import billing, credits, metering
from press_billing.security import get_user_team, is_billing_admin, require_team_access
from press_billing.tax import resolve_tax


@frappe.whitelist()
def whoami() -> dict:
	"""Smoke endpoint: who the SPA is talking as, and their team scope."""
	return {
		"user": frappe.session.user,
		"team": _default_team(),
		"is_billing_admin": is_billing_admin(),
	}


def _default_team() -> str | None:
	"""The team to show by default: the caller's own, or — for an admin browsing
	without a team — any team with data, so the portal is never empty/broken."""
	team = get_user_team()
	if not team and is_billing_admin():
		team = frappe.db.get_value("Subscription", {}, "team")
	return team


def _resolve_team(team: str | None) -> str:
	"""The team to serve: the caller's own (default), gated by access."""
	team = team or _default_team()
	if not team:
		frappe.throw("No billing team in context.", frappe.ValidationError)
	require_team_access(team)
	return team


def _team_clusters(team: str) -> list[str]:
	return [c for c in set(frappe.get_all("Price Lock", {"team": team}, pluck="cluster")) if c]


@frappe.whitelist()
def get_forecast(team: str | None = None) -> dict:
	"""Current-month forecast: projected month-end bill vs credit balance.

	Driven by the same engine billing uses — fixed accrual from the price-lock
	segments (active resources projected to month-end) plus metered overage from
	the running-total rollups.
	"""
	team = _resolve_team(team)
	today = frappe.utils.getdate()
	month_start = frappe.utils.get_first_day(today)
	month_end = frappe.utils.get_last_day(today)

	line_items = []
	for cluster in _team_clusters(team):
		line_items += billing.compute_line_items(team, cluster, month_start, month_end)
		line_items += metering.metered_line_items(team, cluster, month_start, month_end)

	subtotal = frappe.utils.flt(sum(li["amount"] for li in line_items), 2)
	tax = resolve_tax(team, subtotal)
	projected_total = frappe.utils.flt(subtotal + tax["output_tax_amount"], 2)
	credit_balance = frappe.utils.flt(credits.get_balance(team)["balance"])

	return {
		"period_start": str(month_start),
		"period_end": str(month_end),
		"projected_total": projected_total,
		"credit_balance": credit_balance,
		"shortfall": max(0.0, frappe.utils.flt(projected_total - credit_balance, 2)),
		"days_remaining": (month_end - today).days,
		"line_items": line_items,
	}


@frappe.whitelist()
def list_subscriptions(team: str | None = None) -> list[dict]:
	team = _resolve_team(team)
	return frappe.get_all(
		"Subscription",
		filters={"team": team},
		fields=["name", "plan", "cluster", "billing_cycle", "account_standing", "start_date"],
		order_by="creation desc",
	)


@frappe.whitelist()
def list_invoices(team: str | None = None) -> list[dict]:
	"""Invoice history — summary only (no internal/admin fields)."""
	team = _resolve_team(team)
	return frappe.get_all(
		"Invoice",
		filters={"team": team},
		fields=["name", "period_start", "period_end", "status", "invoice_type",
				"total", "amount_paid", "currency", "due_date"],
		order_by="period_start desc",
	)


@frappe.whitelist()
def get_invoice(name: str) -> dict:
	"""One invoice with line items + tax block, scoped to the caller's team."""
	team = frappe.db.get_value("Invoice", name, "team")
	require_team_access(team)
	doc = frappe.get_doc("Invoice", name)
	return {
		"name": doc.name, "team": doc.team, "status": doc.status, "invoice_type": doc.invoice_type,
		"period_start": str(doc.period_start), "period_end": str(doc.period_end),
		"currency": doc.currency, "subtotal": doc.subtotal,
		"output_tax_type": doc.output_tax_type, "output_tax_amount": doc.output_tax_amount,
		"zero_rating_reason": doc.zero_rating_reason, "total": doc.total,
		"credit_applied": doc.credit_applied, "expected_collection": doc.expected_collection,
		"amount_paid": doc.amount_paid, "due_date": str(doc.due_date) if doc.due_date else None,
		"items": [
			{"resource_type": li.resource_type, "plan": li.plan,
			 "subscription_resource": li.subscription_resource,
			 "days": li.days, "quantity": li.quantity, "rate": li.rate, "amount": li.amount}
			for li in doc.items
		],
	}


@frappe.whitelist()
def list_payment_methods(team: str | None = None) -> list[dict]:
	"""Payment methods — display fields only; gateway secrets are never returned."""
	team = _resolve_team(team)
	return frappe.get_all(
		"Payment Method",
		filters={"team": team, "status": ["!=", "cancelled"]},
		fields=["name", "method_type", "status", "display_label", "is_default",
				"expiry_month", "expiry_year"],
		order_by="is_default desc, creation desc",
	)


@frappe.whitelist()
def get_credit_balance(team: str | None = None) -> dict:
	team = _resolve_team(team)
	return {"balance": frappe.utils.flt(credits.get_balance(team)["balance"]), "currency": "INR"}


@frappe.whitelist()
def credit_ledger(team: str | None = None, limit: int = 50) -> list[dict]:
	team = _resolve_team(team)
	return frappe.get_all(
		"Credit Ledger Entry",
		filters={"team": team},
		fields=["entry_type", "amount", "running_balance", "currency", "note", "created_at",
				"reference_type", "reference_name"],
		order_by="creation desc",
		limit=limit,
	)


# --- subscribe / billing profile / credits (customer actions) ---------------


def ensure_billing_team_field():
	"""A User field linking a Billing User to their team (run from after_migrate)."""
	if not frappe.db.exists("Custom Field", "User-billing_team"):
		frappe.get_doc({
			"doctype": "Custom Field", "dt": "User", "fieldname": "billing_team",
			"label": "Billing Team", "fieldtype": "Data", "insert_after": "username",
		}).insert(ignore_permissions=True)


@frappe.whitelist()
def list_plans(currency: str = "INR", cluster: str | None = None) -> list[dict]:
	"""Active catalog for the subscribe form, with the resolved rate."""
	from press_billing.pricing import resolve_rate

	rows = []
	for name in frappe.get_all("Plan", filters={"is_active": 1}, pluck="name"):
		plan = frappe.get_doc("Plan", name)
		rows.append({
			"name": plan.name, "title": plan.title, "billing_cycle": plan.billing_cycle,
			"currency": currency, "rate": frappe.utils.flt(resolve_rate(plan.rates, currency, cluster)),
			"includes": [{"resource_type": i.resource_type, "quantity": i.quantity, "unit": i.unit}
						 for i in plan.includes],
		})
	return rows


@frappe.whitelist()
def get_billing_profile(team: str | None = None) -> dict:
	team = _resolve_team(team)
	if not frappe.db.exists("Billing Profile", team):
		return {"team": team}
	return frappe.get_doc("Billing Profile", team).as_dict()


@frappe.whitelist()
def save_billing_profile(team: str | None = None, **fields) -> dict:
	"""Create/update the team's billing identity (GSTIN validated in the controller)."""
	team = _resolve_team(team)
	allowed = ("legal_name", "email", "phone", "gstin", "address_line1", "address_line2",
			   "city", "state", "country", "pincode")
	values = {k: v for k, v in fields.items() if k in allowed}
	if frappe.db.exists("Billing Profile", team):
		doc = frappe.get_doc("Billing Profile", team)
		doc.update(values)
	else:
		doc = frappe.get_doc({"doctype": "Billing Profile", "team": team, **values})
	doc.save(ignore_permissions=True)
	return {"saved": True, "team": team, "gstin": doc.gstin}


@frappe.whitelist()
def create_subscription(team=None, plan=None, cluster=None, billing_cycle="monthly",
						payment_method=None, gateway=None) -> dict:
	"""Record a subscription INTENT (provisioning happens at the cluster).

	A billing profile is required first — invoicing needs the legal identity.
	"""
	team = _resolve_team(team)
	if not frappe.db.exists("Billing Profile", team):
		frappe.throw("Add your billing details before subscribing.", frappe.ValidationError)
	from press_billing import subscriptions

	doc = subscriptions.create_subscription(
		team=team, cluster=cluster, plan=plan, billing_cycle=billing_cycle,
		default_payment_method=payment_method, gateway=gateway)
	return {"subscription": doc.name, "plan": plan, "account_standing": doc.account_standing}


@frappe.whitelist()
def initiate_card_setup(team=None, gateway=None) -> dict:
	"""Begin adding a card (gateway SetupIntent → client_secret). Real PAN is
	collected client-side by the gateway SDK (PCI), never by our server."""
	team = _resolve_team(team)
	from press_billing import payments

	return payments.initiate_payment_method_setup(team, gateway)


@frappe.whitelist()
def confirm_card(payment_method=None, gateway_method_id=None, display_label=None,
				 expiry_month=None, expiry_year=None) -> dict:
	"""Confirm a card the gateway SDK tokenised — runs the micro-charge validation."""
	from press_billing import payments

	team = frappe.db.get_value("Payment Method", payment_method, "team")
	require_team_access(team)
	method = payments.confirm_payment_method(
		payment_method, gateway_method_id=gateway_method_id, display_label=display_label,
		expiry_month=expiry_month, expiry_year=expiry_year)
	return {"payment_method": method.name, "status": method.status}


@frappe.whitelist()
def add_demo_card(team=None, gateway=None, display_label="Visa ····4242",
				  expiry_month=12, expiry_year=2030) -> dict:
	"""Demo convenience: register an active card without a live gateway round-trip.
	(Production uses initiate_card_setup + confirm_card with the gateway SDK.)"""
	team = _resolve_team(team)
	name = frappe.get_doc({
		"doctype": "Payment Method", "team": team, "gateway": gateway, "method_type": "card",
		"status": "active", "display_label": display_label, "gateway_method_id": f"pm_{frappe.generate_hash(6)}",
		"gateway_customer_id": f"cus_{team}", "expiry_month": expiry_month, "expiry_year": expiry_year,
		"is_default": not frappe.db.exists("Payment Method", {"team": team, "is_default": 1}),
		"validated_at": frappe.utils.now_datetime(),
	}).insert(ignore_permissions=True).name
	return {"payment_method": name, "status": "active"}


@frappe.whitelist()
def purchase_credits(team=None, amount=None, payment_method=None) -> dict:
	"""Top up the prepaid wallet. (The card charge that funds it is the payment
	flow's concern; this books the resulting advance-liability credit.)"""
	team = _resolve_team(team)
	amount = frappe.utils.flt(amount)
	if amount <= 0:
		frappe.throw("Top-up amount must be greater than zero.", frappe.ValidationError)
	from press_billing import credits

	return credits.purchase(team, amount, "INR", payment_method=payment_method, note="Wallet top-up")


@frappe.whitelist()
def pay_invoice(invoice=None) -> dict:
	"""Postpaid one-off settlement of an outstanding invoice (team-scoped)."""
	team = frappe.db.get_value("Invoice", invoice, "team")
	require_team_access(team)
	from press_billing import charges

	return charges.pay_invoice(invoice)


@frappe.whitelist()
def get_billing_settings(team: str | None = None) -> dict:
	"""Payment mode + thresholds (wireframe: Billing Settings)."""
	team = _resolve_team(team)
	if not frappe.db.exists("Billing Profile", team):
		return {"team": team, "billing_mode": "postpaid", "min_balance": 0, "spend_alert_threshold": 0}
	p = frappe.get_doc("Billing Profile", team)
	return {"team": team, "billing_mode": p.billing_mode or "postpaid",
			"min_balance": p.min_balance, "spend_alert_threshold": p.spend_alert_threshold}


@frappe.whitelist()
def save_billing_settings(team=None, billing_mode=None, min_balance=None, spend_alert_threshold=None) -> dict:
	"""Mode changes take effect next billing period (presentation toggle)."""
	team = _resolve_team(team)
	if frappe.db.exists("Billing Profile", team):
		doc = frappe.get_doc("Billing Profile", team)
	else:
		doc = frappe.get_doc({"doctype": "Billing Profile", "team": team, "legal_name": team})
	if billing_mode:
		doc.billing_mode = billing_mode
	if min_balance is not None:
		doc.min_balance = frappe.utils.flt(min_balance)
	if spend_alert_threshold is not None:
		doc.spend_alert_threshold = frappe.utils.flt(spend_alert_threshold)
	doc.save(ignore_permissions=True)
	return {"saved": True, "billing_mode": doc.billing_mode}
