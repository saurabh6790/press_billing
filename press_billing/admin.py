# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Admin dashboard endpoints (issue #19).

Cost-Explorer-style aggregates + drill-down, plus the operational panels. Every
endpoint requires the Billing Admin role — a customer (or the Agent API key)
gets a 403. None of these are team-scoped: an admin sees across all teams.
"""

import frappe

from press_billing import credits
from press_billing.security import require_billing_admin

AGING_BUCKETS = [("0-7", 0, 7), ("8-15", 8, 15), ("16-30", 16, 30), ("30+", 31, 10**9)]
_BILLABLE_LIVE = ("Open", "Paid", "Overdue")


def _period_filter(field, from_date, to_date):
	f = []
	if from_date:
		f.append([field, ">=", from_date])
	if to_date:
		f.append([field, "<=", to_date])
	return f


@frappe.whitelist()
def get_summary(from_date=None, to_date=None) -> dict:
	"""Total billed / collected / outstanding across all teams for the period."""
	require_billing_admin()
	invoices = frappe.get_all(
		"Invoice",
		filters=[["invoice_type", "=", "billable"]] + _period_filter("period_start", from_date, to_date),
		fields=["status", "total", "amount_paid"],
	)
	billed = sum(frappe.utils.flt(i.total) for i in invoices)
	collected = sum(frappe.utils.flt(i.amount_paid) for i in invoices)
	outstanding = sum(
		frappe.utils.flt(i.total) - frappe.utils.flt(i.amount_paid)
		for i in invoices if i.status in ("Open", "Overdue")
	)
	by_status = {}
	for i in invoices:
		by_status[i.status] = by_status.get(i.status, 0) + 1
	return {
		"total_billed": frappe.utils.flt(billed, 2),
		"total_collected": frappe.utils.flt(collected, 2),
		"outstanding": frappe.utils.flt(outstanding, 2),
		"invoice_count": len(invoices),
		"by_status": by_status,
	}


@frappe.whitelist()
def get_cluster_breakdown(from_date=None, to_date=None) -> list[dict]:
	"""Spend by cluster, from the billable invoices' line items."""
	require_billing_admin()
	invoices = frappe.get_all(
		"Invoice",
		filters=[["invoice_type", "=", "billable"]] + _period_filter("period_start", from_date, to_date),
		pluck="name",
	)
	if not invoices:
		return []
	totals = {}
	for li in frappe.get_all(
		"Invoice Line Item", filters={"parent": ["in", invoices]}, fields=["cluster", "amount"]
	):
		totals[li.cluster] = totals.get(li.cluster, 0) + frappe.utils.flt(li.amount)
	return [{"cluster": c or "global", "amount": frappe.utils.flt(a, 2)} for c, a in sorted(totals.items())]


@frappe.whitelist()
def get_team_breakdown(from_date=None, to_date=None) -> list[dict]:
	"""Spend by team (billable invoice totals)."""
	require_billing_admin()
	totals = {}
	for i in frappe.get_all(
		"Invoice",
		filters=[["invoice_type", "=", "billable"]] + _period_filter("period_start", from_date, to_date),
		fields=["team", "total"],
	):
		totals[i.team] = totals.get(i.team, 0) + frappe.utils.flt(i.total)
	rows = [{"team": t, "amount": frappe.utils.flt(a, 2)} for t, a in totals.items()]
	return sorted(rows, key=lambda r: r["amount"], reverse=True)


@frappe.whitelist()
def get_payment_analytics(from_date=None, to_date=None) -> dict:
	"""Attempt → success rate by gateway + failure-reason tally."""
	require_billing_admin()
	attempts = frappe.get_all(
		"Payment Attempt",
		filters=_period_filter("initiated_at", from_date, to_date),
		fields=["gateway", "status", "failure_code"],
	)
	by_gateway = {}
	failure_reasons = {}
	for a in attempts:
		g = by_gateway.setdefault(a.gateway or "unknown", {"total": 0, "captured": 0})
		g["total"] += 1
		if a.status == "captured":
			g["captured"] += 1
		elif a.status == "failed":
			failure_reasons[a.failure_code or "unknown"] = failure_reasons.get(a.failure_code or "unknown", 0) + 1
	for g in by_gateway.values():
		g["success_rate"] = round(g["captured"] / g["total"], 3) if g["total"] else 0
	return {"by_gateway": by_gateway, "failure_reasons": failure_reasons}


@frappe.whitelist()
def get_overdue_aging(now=None) -> dict:
	"""Outstanding Open/Overdue invoices bucketed by days overdue."""
	require_billing_admin()
	today = frappe.utils.getdate(now)
	buckets = {label: {"count": 0, "amount": 0.0} for label, _lo, _hi in AGING_BUCKETS}
	for inv in frappe.get_all(
		"Invoice",
		filters=[["status", "in", ["Open", "Overdue"]], ["invoice_type", "=", "billable"]],
		fields=["total", "amount_paid", "due_date"],
	):
		if not inv.due_date:
			continue
		days = (today - frappe.utils.getdate(inv.due_date)).days
		if days < 0:
			continue
		due = frappe.utils.flt(inv.total) - frappe.utils.flt(inv.amount_paid)
		for label, lo, hi in AGING_BUCKETS:
			if lo <= days <= hi:
				buckets[label]["count"] += 1
				buckets[label]["amount"] = frappe.utils.flt(buckets[label]["amount"] + due, 2)
				break
	return buckets


@frappe.whitelist()
def get_free_trial_costs(from_date=None, to_date=None) -> dict:
	"""Free/trial subsidy (true cost) — cost_report invoices by cluster and plan."""
	require_billing_admin()
	invoices = frappe.get_all(
		"Invoice",
		filters=[["invoice_type", "=", "cost_report"]] + _period_filter("period_start", from_date, to_date),
		fields=["name", "subtotal"],
	)
	total = sum(frappe.utils.flt(i.subtotal) for i in invoices)
	by_cluster, by_plan = {}, {}
	if invoices:
		for li in frappe.get_all(
			"Invoice Line Item", filters={"parent": ["in", [i.name for i in invoices]]},
			fields=["cluster", "plan", "amount"],
		):
			by_cluster[li.cluster or "global"] = by_cluster.get(li.cluster or "global", 0) + frappe.utils.flt(li.amount)
			if li.plan:
				by_plan[li.plan] = by_plan.get(li.plan, 0) + frappe.utils.flt(li.amount)
	return {
		"total_subsidy": frappe.utils.flt(total, 2),
		"by_cluster": {k: frappe.utils.flt(v, 2) for k, v in by_cluster.items()},
		"by_plan": {k: frappe.utils.flt(v, 2) for k, v in by_plan.items()},
	}


@frappe.whitelist()
def get_team_billing(team: str) -> dict:
	"""Team lookup — any team's full billing picture (admin only)."""
	require_billing_admin()
	return {
		"team": team,
		"subscriptions": frappe.get_all(
			"Subscription", filters={"team": team},
			fields=["name", "plan", "cluster", "account_standing"]),
		"invoices": frappe.get_all(
			"Invoice", filters={"team": team},
			fields=["name", "status", "total", "amount_paid", "period_end"], order_by="period_start desc"),
		"payment_attempts": frappe.get_all(
			"Payment Attempt", filters={"team": team},
			fields=["name", "status", "amount", "gateway", "resolved_by"], order_by="creation desc"),
		"credit_balance": frappe.utils.flt(credits.get_balance(team)["balance"]),
	}


@frappe.whitelist()
def update_plan_rate(plan: str, currency: str, rate, cluster: str = "") -> dict:
	"""Price management: change a Plan Rate row. Existing price-locks are
	untouched (they copied the rate at provision) — only new provisions lock the
	new rate. Zero new plans."""
	require_billing_admin()
	doc = frappe.get_doc("Plan", plan)
	for row in doc.rates:
		if row.currency == currency and (row.cluster or "") == (cluster or ""):
			row.rate = rate
			break
	else:
		doc.append("rates", {"currency": currency, "cluster": cluster or None, "rate": rate})
	doc.save(ignore_permissions=True)
	return {"plan": plan, "currency": currency, "cluster": cluster or "global", "rate": frappe.utils.flt(rate)}


_STANDING_RANK = {"current": 0, "past_due": 1, "suspended": 2}


def _plan_monthly_inr(plan: str, cluster: str | None) -> float:
	from press_billing.pricing import resolve_rate

	if not plan or not frappe.db.exists("Plan", plan):
		return 0.0
	doc = frappe.get_doc("Plan", plan)
	return frappe.utils.flt(resolve_rate(doc.rates, "INR", cluster))


@frappe.whitelist()
def get_metrics() -> dict:
	"""Headline reports: team counts, on-time vs delinquent, failures, MRR."""
	require_billing_admin()
	subs = frappe.get_all(
		"Subscription", fields=["team", "plan", "cluster", "account_standing", "billing_cycle"]
	)
	teams, mrr = {}, 0.0
	for s in subs:
		rate = _plan_monthly_inr(s.plan, s.cluster)
		mrr += rate / 12 if s.billing_cycle == "annual" else rate
		cur = teams.get(s.team, "current")
		teams[s.team] = s.account_standing if _STANDING_RANK.get(s.account_standing, 0) > _STANDING_RANK.get(cur, 0) else cur

	on_time = sum(1 for st in teams.values() if st == "current")
	team_count = len(teams)
	return {
		"team_count": team_count,
		"paying_on_time": on_time,
		"delinquent": team_count - on_time,            # past_due or suspended
		"suspended": sum(1 for st in teams.values() if st == "suspended"),
		"payment_failures": frappe.db.count("Payment Attempt", {"status": "failed"}),
		"mrr": frappe.utils.flt(mrr, 2),
		"active_subscriptions": len(subs),
	}


@frappe.whitelist()
def list_teams() -> list[dict]:
	"""Per-team rollup for the admin teams report."""
	require_billing_admin()
	from press_billing import credits

	teams = {}
	for s in frappe.get_all(
		"Subscription", fields=["team", "plan", "cluster", "account_standing", "billing_cycle"]
	):
		t = teams.setdefault(s.team, {"team": s.team, "standing": "current", "mrr": 0.0, "subscriptions": 0})
		rate = _plan_monthly_inr(s.plan, s.cluster)
		t["mrr"] += rate / 12 if s.billing_cycle == "annual" else rate
		t["subscriptions"] += 1
		if _STANDING_RANK.get(s.account_standing, 0) > _STANDING_RANK.get(t["standing"], 0):
			t["standing"] = s.account_standing
	rows = []
	for t in teams.values():
		t["mrr"] = frappe.utils.flt(t["mrr"], 2)
		t["open_invoices"] = frappe.db.count("Invoice", {"team": t["team"], "status": ["in", ["Open", "Overdue"]]})
		t["credit_balance"] = frappe.utils.flt(credits.get_balance(t["team"])["balance"])
		rows.append(t)
	return sorted(rows, key=lambda r: r["mrr"], reverse=True)
