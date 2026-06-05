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
# Teams bill in mixed currencies; normalise revenue to INR for one comparable axis.
_FX_TO_INR = {"INR": 1.0, "EUR": 90.0, "USD": 83.0}
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _period_filter(field, from_date, to_date):
	f = []
	if from_date:
		f.append([field, ">=", from_date])
	if to_date:
		f.append([field, "<=", to_date])
	return f


def _to_inr(amount, currency) -> float:
	"""Normalise a native-currency amount to an INR-equivalent for cross-team
	aggregates (teams bill in INR/EUR/USD; summing raw would be meaningless)."""
	return frappe.utils.flt(amount) * _FX_TO_INR.get(currency, 1.0)


@frappe.whitelist()
def get_summary(from_date=None, to_date=None) -> dict:
	"""Total billed / collected / outstanding across all teams (INR-equivalent)."""
	require_billing_admin()
	invoices = frappe.get_all(
		"Invoice",
		filters=[["invoice_type", "=", "billable"]] + _period_filter("period_start", from_date, to_date),
		fields=["status", "total", "amount_paid", "currency"],
	)
	billed = sum(_to_inr(i.total, i.currency) for i in invoices)
	collected = sum(_to_inr(i.amount_paid, i.currency) for i in invoices)
	outstanding = sum(
		_to_inr(i.total, i.currency) - _to_inr(i.amount_paid, i.currency)
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
		"currency": "INR",
	}


@frappe.whitelist()
def get_revenue_trend(months: int = 12) -> list[dict]:
	"""Monthly billed vs collected (INR-normalised) — the headline revenue chart.

	Invoices carry mixed currencies, so each is converted to INR at a flat demo FX
	rate before bucketing by billing month, giving one comparable revenue axis.
	"""
	require_billing_admin()
	buckets = {}
	for inv in frappe.get_all(
		"Invoice",
		filters={"invoice_type": "billable"},
		fields=["period_start", "total", "amount_paid", "currency"],
	):
		if not inv.period_start:
			continue
		key = str(inv.period_start)[:7]  # YYYY-MM
		fx = _FX_TO_INR.get(inv.currency, 1.0)
		b = buckets.setdefault(key, {"billed": 0.0, "collected": 0.0})
		b["billed"] += frappe.utils.flt(inv.total) * fx
		b["collected"] += frappe.utils.flt(inv.amount_paid) * fx
	rows = []
	for key in sorted(buckets)[-months:]:
		y, m = key.split("-")
		rows.append({
			"month": key,
			"label": f"{_MONTHS[int(m) - 1]} {y[2:]}",
			"billed": frappe.utils.flt(buckets[key]["billed"], 2),
			"collected": frappe.utils.flt(buckets[key]["collected"], 2),
		})
	return rows


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
	"""Team lookup — any team's full billing picture (admin only).

	Amounts here are in the team's OWN billing currency (not INR-normalised) —
	this is the record-level view, so €/$ teams read in their real currency.
	"""
	require_billing_admin()
	currency = _team_currency(team)
	return {
		"team": team,
		"currency": currency,
		"tier": frappe.db.get_value("Trust Tier", team, "tier") or "—",
		"subscriptions": frappe.get_all(
			"Subscription", filters={"team": team},
			fields=["name", "plan", "cluster", "account_standing"]),
		"invoices": frappe.get_all(
			"Invoice", filters={"team": team},
			fields=["name", "status", "total", "amount_paid", "currency", "period_end"], order_by="period_start desc"),
		"payment_attempts": frappe.get_all(
			"Payment Attempt", filters={"team": team},
			fields=["name", "status", "amount", "currency", "gateway", "failure_code", "resolved_by"], order_by="creation desc"),
		"credit_balance": frappe.utils.flt(credits.get_balance(team)["balance"]),
	}


@frappe.whitelist()
def list_all_invoices(status: str = None, team: str = None, limit: int = 500) -> list[dict]:
	"""Global invoice list (admin) with optional status/team filters — the
	drill-down target for the Collected / Outstanding cards.

	`status` accepts a literal Invoice status (Paid/Open/Overdue/Draft/…) or the
	pseudo-filters `outstanding` (Open+Overdue) and `paid`.
	"""
	require_billing_admin()
	filters = {"invoice_type": "billable"}
	if team:
		filters["team"] = team
	if status == "outstanding":
		filters["status"] = ["in", ["Open", "Overdue"]]
	elif status == "paid":
		filters["status"] = "Paid"
	elif status:
		filters["status"] = status.title()
	rows = frappe.get_all(
		"Invoice", filters=filters,
		fields=["name", "team", "status", "total", "amount_paid", "currency",
				"period_start", "period_end", "due_date"],
		order_by="period_start desc, team asc", limit=limit,
	)
	for r in rows:
		r["outstanding"] = frappe.utils.flt(frappe.utils.flt(r.total) - frappe.utils.flt(r.amount_paid), 2)
	return rows


@frappe.whitelist()
def get_catalog() -> dict:
	"""Products & infrastructure: plans (with INR base rate), add-ons, and the
	clusters teams run in (with active resource counts)."""
	require_billing_admin()
	plans = []
	for p in frappe.get_all("Plan", fields=["name", "title", "billing_cycle", "is_active"], order_by="name asc"):
		plans.append({
			**p,
			"inr_rate": _plan_monthly_inr(p.name, None),
			"active_resources": frappe.db.count("Price Lock", {"plan": p.name, "ended_at": ["is", "not set"]}),
		})
	addons = frappe.get_all("Add-on", fields=["name", "title", "resource_type", "unit", "billing_type"], order_by="name asc")
	clusters = {}
	for lock in _active_locks():
		c = clusters.setdefault(lock.cluster or "global", {"cluster": lock.cluster or "global", "resources": 0, "teams": set()})
		c["resources"] += 1
		c["teams"].add(lock.team)
	cluster_rows = sorted(
		({"cluster": c["cluster"], "resources": c["resources"], "teams": len(c["teams"])} for c in clusters.values()),
		key=lambda r: r["resources"], reverse=True,
	)
	return {"plans": plans, "addons": addons, "clusters": cluster_rows}


@frappe.whitelist()
def get_retention() -> dict:
	"""Customer retention snapshot: active vs at-risk vs churned, and a retention
	rate. A team is churned when its only standing is suspended; at-risk when
	past_due; retained otherwise."""
	require_billing_admin()
	standing = {}
	for s in frappe.get_all("Subscription", fields=["team", "account_standing"]):
		cur = standing.get(s.team, "current")
		standing[s.team] = s.account_standing if _STANDING_RANK.get(s.account_standing, 0) > _STANDING_RANK.get(cur, 0) else cur
	total = len(standing)
	active = sum(1 for v in standing.values() if v == "current")
	at_risk = sum(1 for v in standing.values() if v == "past_due")
	churned = sum(1 for v in standing.values() if v == "suspended")
	rows = [{"team": t, "standing": v} for t, v in sorted(standing.items())]
	return {
		"total_teams": total,
		"active": active,
		"at_risk": at_risk,
		"churned": churned,
		"retention_rate": round((total - churned) / total, 3) if total else 0,
		"active_rate": round(active / total, 3) if total else 0,
		"teams": rows,
	}


@frappe.whitelist()
def update_plan_rate(plan: str, currency: str, rate, cluster: str = "") -> dict:
	"""Price management: change a plan's Catalog Rate. Existing price-locks are
	untouched (they copied the rate at provision) — only new provisions lock the
	new rate. Zero new plans."""
	require_billing_admin()
	if not frappe.db.exists("Plan", plan):
		frappe.throw(f"Plan {plan!r} does not exist.")
	cluster = cluster or None

	existing = frappe.get_all(
		"Catalog Rate",
		filters={"priced_doctype": "Plan", "priced_for": plan, "currency": currency},
		fields=["name", "cluster"],
	)
	match = next((r for r in existing if (r.cluster or None) == cluster), None)
	if match:
		frappe.db.set_value("Catalog Rate", match.name, "rate", rate)
	else:
		frappe.get_doc(
			{
				"doctype": "Catalog Rate",
				"priced_doctype": "Plan",
				"priced_for": plan,
				"currency": currency,
				"cluster": cluster,
				"rate": rate,
			}
		).insert(ignore_permissions=True)
	return {"plan": plan, "currency": currency, "cluster": cluster or "global", "rate": frappe.utils.flt(rate)}


_STANDING_RANK = {"current": 0, "past_due": 1, "suspended": 2}


def _plan_monthly_inr(plan: str, cluster: str | None) -> float:
	from press_billing.pricing import get_catalog_rates, resolve_rate

	if not plan or not frappe.db.exists("Plan", plan):
		return 0.0
	return frappe.utils.flt(resolve_rate(get_catalog_rates("Plan", plan), "INR", cluster))


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




def _active_locks(filters=None):
	f = {"ended_at": ["is", "not set"]}
	if filters:
		f.update(filters)
	return frappe.get_all("Price Lock", filters=f, fields=["team", "cluster", "plan", "locked_rate"])


@frappe.whitelist()
def list_teams() -> list[dict]:
	"""Per-team rollup: standing, tier, MRR, resources, open invoices, credit."""
	require_billing_admin()
	from press_billing import credits

	teams = {}
	for s in frappe.get_all("Subscription", fields=["team", "plan", "cluster", "account_standing", "billing_cycle"]):
		t = teams.setdefault(s.team, {"team": s.team, "standing": "current", "mrr": 0.0, "subscriptions": 0, "resources": 0})
		rate = _plan_monthly_inr(s.plan, s.cluster)
		t["mrr"] += rate / 12 if s.billing_cycle == "annual" else rate
		t["subscriptions"] += 1
		if _STANDING_RANK.get(s.account_standing, 0) > _STANDING_RANK.get(t["standing"], 0):
			t["standing"] = s.account_standing
	for lock in _active_locks():
		if lock.team in teams:
			teams[lock.team]["resources"] += 1
	rows = []
	for t in teams.values():
		currency = _team_currency(t["team"])
		t["mrr"] = frappe.utils.flt(t["mrr"], 2)
		t["tier"] = frappe.db.get_value("Trust Tier", t["team"], "tier") or "—"
		t["open_invoices"] = frappe.db.count("Invoice", {"team": t["team"], "status": ["in", ["Open", "Overdue"]]})
		t["invoices"] = frappe.db.count("Invoice", {"team": t["team"]})
		# Credit normalised to INR so the whole row reads on one (INR-equiv.) axis.
		t["credit_balance"] = frappe.utils.flt(_to_inr(credits.get_balance(t["team"])["balance"], currency), 2)
		t["currency"] = currency
		rows.append(t)
	return sorted(rows, key=lambda r: r["mrr"], reverse=True)


def _team_currency(team: str) -> str:
	return frappe.db.get_value("Price Lock", {"team": team}, "currency") or "INR"


@frappe.whitelist()
def get_payment_failures(limit: int = 50) -> list[dict]:
	"""Drill-down: which charges are failing and why."""
	require_billing_admin()
	return frappe.get_all(
		"Payment Attempt", filters={"status": "failed"},
		fields=["name", "team", "invoice", "amount", "currency", "gateway", "failure_code", "failure_reason", "creation"],
		order_by="creation desc", limit=limit)


@frappe.whitelist()
def get_delinquent_teams() -> list[dict]:
	"""Drill-down: who is past_due/suspended + their outstanding invoices."""
	require_billing_admin()
	seen, rows = set(), []
	for s in frappe.get_all("Subscription", filters=[["account_standing", "in", ["past_due", "suspended"]]],
			fields=["team", "account_standing"]):
		if s.team in seen:
			continue
		seen.add(s.team)
		overdue = frappe.get_all("Invoice", filters={"team": s.team, "status": ["in", ["Open", "Overdue"]]},
			fields=["name", "status", "total", "amount_paid", "due_date"], order_by="due_date asc")
		rows.append({"team": s.team, "standing": s.account_standing,
			"outstanding": frappe.utils.flt(sum(frappe.utils.flt(i.total) - frappe.utils.flt(i.amount_paid) for i in overdue), 2),
			"invoices": overdue})
	return rows


@frappe.whitelist()
def get_cluster_consumption() -> list[dict]:
	"""Cluster-wise resource consumption (active price-locks) + monthly run-rate.

	Run-rate is normalised to INR (via each plan's INR catalog rate) so regions
	billed in EUR/USD are comparable on one axis.
	"""
	require_billing_admin()
	out = {}
	for lock in _active_locks():
		c = out.setdefault(lock.cluster or "global", {"cluster": lock.cluster or "global", "resources": 0, "monthly": 0.0, "currency": "INR"})
		c["resources"] += 1
		c["monthly"] = frappe.utils.flt(c["monthly"] + _plan_monthly_inr(lock.plan, lock.cluster), 2)
	return sorted(out.values(), key=lambda r: r["monthly"], reverse=True)


@frappe.whitelist()
def get_plan_consumption() -> list[dict]:
	"""Plan-wise consumption analysis (INR-normalised monthly run-rate)."""
	require_billing_admin()
	out = {}
	for lock in _active_locks():
		p = out.setdefault(lock.plan or "—", {"plan": lock.plan or "—", "resources": 0, "monthly": 0.0, "currency": "INR"})
		p["resources"] += 1
		p["monthly"] = frappe.utils.flt(p["monthly"] + _plan_monthly_inr(lock.plan, lock.cluster), 2)
	return sorted(out.values(), key=lambda r: r["monthly"], reverse=True)


@frappe.whitelist()
def get_conversion() -> dict:
	"""Trial → paid conversion."""
	require_billing_admin()
	from press_billing.trials import entry_tier

	entry = entry_tier()
	tiers = frappe.get_all("Trust Tier", fields=["team", "tier", "promotion_basis"])
	total = len(tiers)
	trial = sum(1 for t in tiers if t.tier == entry)
	paid = total - trial
	converted = sum(1 for t in tiers if (t.promotion_basis or "").startswith("converted"))
	return {"total_teams": total, "trial": trial, "paid": paid, "converted": converted,
			"conversion_rate": round(paid / total, 3) if total else 0}


@frappe.whitelist()
def get_trial_detail() -> dict:
	"""Trial subsidy analysis with full provenance: how many teams are still on
	trial, the per-team subsidy, and the exact cost_report invoices the total is
	summed from (so 'where does ₹X come from?' is answerable)."""
	require_billing_admin()
	from press_billing.trials import entry_tier

	entry = entry_tier()
	invoices = frappe.get_all(
		"Invoice", filters={"invoice_type": "cost_report"},
		fields=["name", "team", "subtotal", "currency", "period_start", "period_end"],
		order_by="period_start desc",
	)
	by_team = {}
	still_on_trial, converted_subsidy, trial_subsidy = 0.0, 0.0, 0.0
	for inv in invoices:
		tier = frappe.db.get_value("Trust Tier", inv.team, "tier")
		on_trial = tier == entry
		inr = _to_inr(inv.subtotal, inv.currency)
		t = by_team.setdefault(inv.team, {"team": inv.team, "on_trial": on_trial, "tier": tier or "—",
											"subsidy": 0.0, "currency": inv.currency, "invoices": []})
		t["subsidy"] = frappe.utils.flt(t["subsidy"] + frappe.utils.flt(inv.subtotal), 2)
		t["invoices"].append({"name": inv.name, "subtotal": frappe.utils.flt(inv.subtotal, 2),
							   "period_start": str(inv.period_start), "period_end": str(inv.period_end)})
		if on_trial:
			trial_subsidy += inr
		else:
			converted_subsidy += inr
	teams = sorted(by_team.values(), key=lambda r: r["subsidy"], reverse=True)
	return {
		"entry_tier": entry,
		"still_on_trial": sum(1 for t in teams if t["on_trial"]),
		"converted": sum(1 for t in teams if not t["on_trial"]),
		"trial_subsidy_inr": frappe.utils.flt(trial_subsidy, 2),
		"converted_subsidy_inr": frappe.utils.flt(converted_subsidy, 2),
		"total_subsidy_inr": frappe.utils.flt(trial_subsidy + converted_subsidy, 2),
		"teams": teams,
	}


@frappe.whitelist()
def get_trial_costs_detail() -> dict:
	"""Trial subsidy split: still-on-trial (unconverted) vs converted-to-paid."""
	require_billing_admin()
	from press_billing.trials import entry_tier

	entry = entry_tier()
	unconverted, converted = 0.0, 0.0
	for inv in frappe.get_all("Invoice", filters={"invoice_type": "cost_report"}, fields=["team", "subtotal"]):
		tier = frappe.db.get_value("Trust Tier", inv.team, "tier")
		if tier == entry:
			unconverted += frappe.utils.flt(inv.subtotal)
		else:
			converted += frappe.utils.flt(inv.subtotal)
	return {"unconverted_subsidy": frappe.utils.flt(unconverted, 2),
			"converted_cost": frappe.utils.flt(converted, 2),
			"total": frappe.utils.flt(unconverted + converted, 2)}
