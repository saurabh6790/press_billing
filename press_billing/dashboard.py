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
		"team": get_user_team(),
		"is_billing_admin": is_billing_admin(),
	}


def _resolve_team(team: str | None) -> str:
	"""The team to serve: the caller's own (default), gated by access."""
	team = team or get_user_team()
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
