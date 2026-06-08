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

from billing import billing, credits, metering
from billing.security import get_user_team, is_billing_admin, require_team_access
from billing.tax import resolve_tax


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


def _team_currency(team: str) -> str:
	"""A team bills in a single currency — read it off any of its price-locks."""
	return frappe.db.get_value("Price Lock", {"team": team}, "currency") or "INR"


def _gateway_for_currency(currency: str) -> str:
	"""Pick the enabled gateway that settles in this currency (e.g. EUR → Stripe,
	INR → Razorpay), preferring the one flagged default-for-currency. A team must
	never be sent to a gateway that can't take its currency."""
	gw = (frappe.db.get_value("Payment Gateway",
			{"currency": currency, "is_enabled": 1, "is_default_for_currency": 1}, "name")
		or frappe.db.get_value("Payment Gateway",
			{"currency": currency, "is_enabled": 1}, "name"))
	if not gw:
		frappe.throw(f"No payment gateway configured for {currency} top-ups.", frappe.ValidationError)
	return gw


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
	mode = frappe.db.get_value("Billing Profile", team, "billing_mode") or "postpaid"
	shortfall = max(0.0, frappe.utils.flt(projected_total - credit_balance, 2))
	currency = frappe.db.get_value("Price Lock", {"team": team}, "currency") or "INR"

	return {
		"period_start": str(month_start),
		"period_end": str(month_end),
		"projected_total": projected_total,
		"subtotal": subtotal,
		"tax_amount": tax["output_tax_amount"],
		"tax_type": tax["output_tax_type"],
		"credit_balance": credit_balance,
		"shortfall": shortfall,
		"days_remaining": (month_end - today).days,
		"billing_mode": mode,
		"currency": currency,
		# On prepaid, warn when the projected bill outruns the wallet.
		"credit_alert": mode == "prepaid" and shortfall > 0,
		# Spell out each service/plan + metered overage driving the projection.
		"line_items": [_describe_line(team, frappe._dict(li)) for li in line_items],
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
		"items": [_describe_line(doc.team, li) for li in doc.items],
	}


def _describe_line(team: str, li) -> dict:
	"""Turn a stored line item into a human-readable charge row.

	Resource slugs and plan IDs mean nothing to a customer, so we resolve the
	plan/add-on TITLE and spell out what drove the charge: a plan's monthly fee
	(prorated days), or a metered overage above the plan's included allowance.
	"""
	row = {
		"resource_type": li.resource_type, "plan": li.plan,
		"subscription_resource": li.subscription_resource,
		"days": li.days, "quantity": li.quantity, "rate": li.rate, "amount": li.amount,
		"unit": li.unit,
	}
	if li.resource_type == "bundle":
		title = frappe.db.get_value("Plan", li.plan, "title") if li.plan else None
		row["item"] = title or li.plan or "Subscription plan"
		row["kind"] = "Plan"
		row["detail"] = f"{li.days} day(s) this period" if li.days else None
	else:
		addon = frappe.db.get_value("Add-on", {"resource_type": li.resource_type}, ["title"])
		row["item"] = addon or f"{li.resource_type.title()} overage"
		row["kind"] = "Overage"
		# Surface the included allowance the usage ran past, so the bill is legible.
		allowance = frappe.db.get_value(
			"Usage Rollup",
			{"team": team, "resource_id": li.subscription_resource, "resource_type": li.resource_type},
			"locked_allowance",
		)
		unit = li.unit or "units"
		if allowance is not None:
			row["detail"] = f"{frappe.utils.flt(li.quantity):g} {unit} over {frappe.utils.flt(allowance):g} {unit} included"
		else:
			row["detail"] = f"{frappe.utils.flt(li.quantity):g} {unit} metered"
	return row


@frappe.whitelist()
def list_payment_attempts(team: str | None = None, limit: int = 100) -> list[dict]:
	"""Payment attempt history — every charge against the team's card/mandate,
	including the failed dunning retries that lead to suspension. This is the
	customer's record of WHY a card-on-file team can still be past_due/suspended.
	"""
	team = _resolve_team(team)
	return frappe.get_all(
		"Payment Attempt",
		filters={"team": team},
		fields=["name", "status", "amount", "currency", "gateway", "invoice",
				"failure_code", "failure_reason", "retry_number",
				"gateway_transaction_id", "creation"],
		order_by="creation desc",
		limit=limit,
	)


@frappe.whitelist()
def list_payment_methods(team: str | None = None) -> list[dict]:
	"""Payment methods — display fields only; gateway secrets are never returned."""
	team = _resolve_team(team)
	return frappe.get_all(
		"Payment Method",
		filters={"team": team, "status": ["!=", "cancelled"]},
		fields=["name", "method_type", "status", "display_label", "is_default", "priority",
				"reauth_required", "expiry_month", "expiry_year"],
		order_by="priority asc, creation asc",
	)


@frappe.whitelist()
def get_credit_balance(team: str | None = None) -> dict:
	team = _resolve_team(team)
	return {"balance": frappe.utils.flt(credits.get_balance(team)["balance"]), "currency": _team_currency(team)}


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
def initiate_card_setup(team=None, gateway=None) -> dict:
	"""Begin adding a card (gateway SetupIntent → client_secret). Real PAN is
	collected client-side by the gateway SDK (PCI), never by our server."""
	team = _resolve_team(team)
	from billing import payments

	return payments.initiate_payment_method_setup(team, gateway)


@frappe.whitelist()
def confirm_card(payment_method=None, gateway_method_id=None, display_label=None,
				 expiry_month=None, expiry_year=None) -> dict:
	"""Confirm a card the gateway SDK tokenised — runs the micro-charge validation."""
	from billing import payments

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
	from billing import payments

	name = frappe.get_doc({
		"doctype": "Payment Method", "team": team, "gateway": gateway, "method_type": "card",
		"status": "active", "display_label": display_label, "gateway_method_id": f"pm_{frappe.generate_hash(6)}",
		"gateway_customer_id": f"cus_{team}", "expiry_month": expiry_month, "expiry_year": expiry_year,
		"validated_at": frappe.utils.now_datetime(),
	}).insert(ignore_permissions=True).name
	payments.densify_priorities(team)  # append at the end of the fallback order
	return {"payment_method": name, "status": "active"}


@frappe.whitelist()
def purchase_credits(team=None, amount=None, payment_method=None) -> dict:
	"""Top up the prepaid wallet. (The card charge that funds it is the payment
	flow's concern; this books the resulting advance-liability credit.)"""
	team = _resolve_team(team)
	amount = frappe.utils.flt(amount)
	if amount <= 0:
		frappe.throw("Top-up amount must be greater than zero.", frappe.ValidationError)
	from billing import credits

	return credits.purchase(team, amount, "INR", payment_method=payment_method, note="Wallet top-up")


@frappe.whitelist()
def pay_invoice(invoice=None) -> dict:
	"""Postpaid one-off settlement of an outstanding invoice (team-scoped)."""
	team = frappe.db.get_value("Invoice", invoice, "team")
	require_team_access(team)
	from billing import charges

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


# --- real gateway top-up (Razorpay Checkout / Stripe PaymentIntent) ----------


@frappe.whitelist()
def create_topup_order(team=None, amount=None, gateway=None) -> dict:
	"""Start a wallet top-up by creating a real gateway order. The UI opens the
	gateway's checkout against it; the wallet is credited only after the gateway
	confirms (verify in confirm_topup) — never magically."""
	team = _resolve_team(team)
	amount = frappe.utils.flt(amount)
	if amount <= 0:
		frappe.throw("Top-up amount must be greater than zero.", frappe.ValidationError)
	currency = _team_currency(team)
	gw = gateway or _gateway_for_currency(currency)
	from billing.gateways.registry import get_adapter

	gw_doc = frappe.get_doc("Payment Gateway", gw)
	adapter = get_adapter(gw_doc)
	receipt = f"topup-{team}-{frappe.generate_hash(8)}"
	notes = {"team": team, "purpose": "wallet_topup"}
	if gw_doc.adapter_key == "stripe":
		# Hosted Stripe Checkout: the SPA redirects out and returns to /billing/credits,
		# which confirms the session. Stripe fills in {CHECKOUT_SESSION_ID}.
		from urllib.parse import quote

		base = frappe.utils.get_url()
		success_url = (f"{base}/billing/credits?topup=success&gateway={quote(gw)}"
					   f"&team={quote(team)}&session={{CHECKOUT_SESSION_ID}}")
		cancel_url = f"{base}/billing/credits?topup=cancelled"
		handles = adapter.create_checkout_session(amount, currency, receipt, success_url, cancel_url, notes=notes)
	else:
		handles = adapter.create_order(amount, currency, receipt, notes=notes)
	return {"gateway": gw, "adapter_key": gw_doc.adapter_key,
			"amount": amount, "currency": currency, "receipt": receipt, **handles}


@frappe.whitelist()
def confirm_topup(team=None, amount=None, gateway=None, razorpay_order_id=None,
				  razorpay_payment_id=None, razorpay_signature=None, session=None) -> dict:
	"""Credit the wallet only after the gateway confirms the money really moved.
	Razorpay confirms via the checkout-callback signature; Stripe confirms by
	retrieving the hosted Checkout session and checking it was paid (and credits
	the server-confirmed amount, not a client-supplied one). The wallet is credited
	in the team's own currency — never assumed INR."""
	team = _resolve_team(team)
	currency = _team_currency(team)
	amount = frappe.utils.flt(amount)
	from billing.gateways.registry import get_adapter

	gw_doc = frappe.get_doc("Payment Gateway", gateway)
	adapter = get_adapter(gw_doc)
	if gw_doc.adapter_key == "razorpay":
		ok = adapter.verify_payment_signature({
			"razorpay_order_id": razorpay_order_id,
			"razorpay_payment_id": razorpay_payment_id,
			"razorpay_signature": razorpay_signature,
		})
		reference = razorpay_payment_id
	else:
		# Hosted-checkout gateways (Stripe): trust the session the gateway confirms,
		# including the amount/currency it actually charged.
		checkout = adapter.get_checkout_session(session)
		ok = checkout.get("payment_status") == "paid"
		reference = checkout.get("payment_intent")
		if checkout.get("amount_total"):
			amount = frappe.utils.flt(checkout["amount_total"]) / 100
		if checkout.get("currency"):
			currency = checkout["currency"].upper()
	if not ok:
		frappe.throw("Payment confirmation failed.", frappe.ValidationError)
	from billing import credits

	return credits.purchase(team, amount, currency,
		reference_name=reference, note=f"Wallet top-up ({reference})")


def _add_method_gateway(currency: str):
	"""Gateway to add a payment method in this currency.

	A Razorpay gateway (if one exists for the currency) wins, because only
	Razorpay carries UPI Autopay — picking by *adapter* not by
	`is_default_for_currency`, since the demo flags a Stripe-INR gateway as the
	INR default which must not hide UPI. Otherwise the currency's gateway
	(Stripe = card only)."""
	rzp = frappe.db.get_value(
		"Payment Gateway",
		{"currency": currency, "adapter_key": "razorpay", "is_enabled": 1},
		["name", "adapter_key"], as_dict=True, order_by="is_default_for_currency desc",
	)
	if rzp:
		return rzp
	return frappe.db.get_value(
		"Payment Gateway", {"currency": currency, "is_enabled": 1},
		["name", "adapter_key"], as_dict=True, order_by="is_default_for_currency desc",
	) or frappe._dict()


@frappe.whitelist()
def get_payment_method_options(team=None) -> dict:
	"""What the team can set up, resolved from their billing currency: card + UPI
	on Razorpay (INR), card-only on Stripe (USD/EUR). UPI is gated by the
	₹1,00,000 recurring limit."""
	team = _resolve_team(team)
	currency = _team_currency(team)
	gw = _add_method_gateway(currency)

	if gw.get("adapter_key") == "razorpay":
		from billing import mandates

		elig = mandates.upi_eligibility(team)
		return {"gateway": gw.name, "adapter_key": "razorpay", "currency": currency,
				"methods": ["card", "upi_autopay"], "allow_upi": elig["eligible"],
				"upi_block_reason": elig["reason"], "upi_limit": elig["limit"]}

	publishable_key = None
	if gw.get("adapter_key") == "stripe":
		from billing.gateways.registry import get_adapter

		publishable_key = get_adapter(frappe.get_doc("Payment Gateway", gw.name)).get_credential("api_key")
	return {"gateway": gw.get("name"), "adapter_key": gw.get("adapter_key"), "currency": currency,
			"methods": ["card"], "allow_upi": False, "upi_block_reason": None, "upi_limit": None,
			"publishable_key": publishable_key}


@frappe.whitelist()
def setup_payment_method_order(team=None, gateway=None, method_type="upi_autopay") -> dict:
	"""Begin adding a Razorpay recurring method — UPI Autopay mandate (ceiling =
	trust-tier cap) or a card token. Returns the order handles the UI runs
	Razorpay Checkout against (#08)."""
	team = _resolve_team(team)
	gw = gateway or _add_method_gateway(_team_currency(team)).get("name")
	from billing import mandates

	if method_type == "card":
		return mandates.setup_card(team, gw)
	return mandates.setup_mandate(team, gw)


@frappe.whitelist()
def confirm_payment_method_order(payment_method=None, razorpay_payment_id=None,
								 razorpay_order_id=None, razorpay_signature=None, razorpay_token_id=None) -> dict:
	"""Confirm the Razorpay Checkout callback — verifies the signature, activates
	the mandate. Real gateway verification, not a stub."""
	team = frappe.db.get_value("Payment Method", payment_method, "team")
	require_team_access(team)
	from billing import mandates

	method = mandates.confirm_mandate(payment_method, {
		"razorpay_payment_id": razorpay_payment_id, "razorpay_order_id": razorpay_order_id,
		"razorpay_signature": razorpay_signature, "razorpay_token_id": razorpay_token_id,
	})
	return {"payment_method": method.name, "status": method.status}


# Tier caps (max_spend) are stored in INR; convert to the team's billing currency
# so a EUR/USD team sees a coherent cap-vs-spend comparison.
_FX_TO_INR = {"INR": 1.0, "EUR": 90.0, "USD": 83.0}


def _from_inr(amount: float, currency: str) -> float:
	return frappe.utils.flt(frappe.utils.flt(amount) / _FX_TO_INR.get(currency, 1.0), 2)


@frappe.whitelist()
def get_team_overview(team: str | None = None) -> dict:
	"""Team header: trust tier, account standing, payment mode, resource count."""
	team = _resolve_team(team)
	tier = frappe.db.get_value("Trust Tier", team, ["tier", "max_spend"], as_dict=True) or {}
	standing = frappe.db.get_value("Subscription", {"team": team}, "account_standing") or "current"
	mode = frappe.db.get_value("Billing Profile", team, "billing_mode") or "postpaid"
	resources = frappe.db.count("Price Lock", {"team": team, "ended_at": ["is", "not set"]})
	clusters = len(_team_clusters(team))
	currency = _team_currency(team)
	return {"team": team, "tier": tier.get("tier"),
			"max_spend": _from_inr(tier.get("max_spend"), currency),
			"standing": standing, "billing_mode": mode, "resources": resources, "clusters": clusters,
			"currency": currency}


@frappe.whitelist()
def get_trust_tier(team: str | None = None) -> dict:
	"""What the team's trust tier offers, and how to reach the next level.

	Returns the current tier's limits (spend cap in billing currency, resource
	cap), the team's progress (resources used, paid invoices, cumulative paid),
	and the NEXT tier's promotion criteria — so a customer can see what unlocks
	more headroom.
	"""
	team = _resolve_team(team)
	currency = _team_currency(team)
	tt = frappe.db.get_value("Trust Tier", team, ["tier", "level", "max_spend", "max_resource_count"], as_dict=True) or {}

	levels = frappe.get_all(
		"Trust Tier Level",
		fields=["name", "tier", "sequence", "max_spend", "max_resource_count",
				"min_paid_invoices", "min_cumulative_paid"],
		order_by="sequence asc",
	)
	current_seq = next((l.sequence for l in levels if l.tier == tt.get("tier")), None)
	current = next((l for l in levels if l.tier == tt.get("tier")), None)
	nxt = next((l for l in levels if current_seq is not None and l.sequence == current_seq + 1), None)

	# Progress signals toward the next level.
	resources_used = frappe.db.count("Price Lock", {"team": team, "ended_at": ["is", "not set"]})
	paid_invoices = frappe.db.count("Invoice", {"team": team, "status": "Paid", "invoice_type": "billable"})
	paid_rows = frappe.get_all("Invoice", {"team": team, "status": "Paid", "invoice_type": "billable"},
							   ["amount_paid", "currency"])
	cumulative_paid_inr = sum(frappe.utils.flt(r.amount_paid) * _FX_TO_INR.get(r.currency, 1.0) for r in paid_rows)

	def level_view(l):
		if not l:
			return None
		return {
			"tier": l.tier, "sequence": l.sequence,
			"max_spend": _from_inr(l.max_spend, currency),
			"max_resource_count": l.max_resource_count,
			"min_paid_invoices": l.min_paid_invoices,
			"min_cumulative_paid": _from_inr(l.min_cumulative_paid, currency),
		}

	return {
		"team": team, "currency": currency,
		"current": level_view(current),
		"next": level_view(nxt),
		"is_top_tier": nxt is None,
		"progress": {
			"resources_used": resources_used,
			"paid_invoices": paid_invoices,
			"cumulative_paid": _from_inr(cumulative_paid_inr, currency),
		},
		"all_levels": [level_view(l) for l in levels],
	}


@frappe.whitelist()
def list_switchable_teams() -> list[dict]:
	"""POC team switcher — teams that have billing data, with their tier/standing."""
	teams = sorted(t for t in set(frappe.get_all("Subscription", pluck="team"))
				   | set(frappe.get_all("Billing Profile", pluck="team")) if t)
	out = []
	for t in teams:
		out.append({"team": t, "tier": frappe.db.get_value("Trust Tier", t, "tier"),
					"standing": frappe.db.get_value("Subscription", {"team": t}, "account_standing") or "current"})
	return out


@frappe.whitelist()
def remove_payment_method(payment_method=None) -> dict:
	"""Remove a card/mandate; promotes another active method to default."""
	team = frappe.db.get_value("Payment Method", payment_method, "team")
	require_team_access(team)
	from billing import payments

	return payments.delete_payment_method(payment_method)


@frappe.whitelist()
def set_default_payment_method(payment_method=None) -> dict:
	team = frappe.db.get_value("Payment Method", payment_method, "team")
	require_team_access(team)
	from billing import payments

	doc = payments.set_default_payment_method(payment_method)
	return {"payment_method": doc.name, "is_default": doc.is_default, "priority": doc.priority}


@frappe.whitelist()
def reorder_payment_methods(team=None, ordered=None) -> dict:
	"""Set the team's fallback order (primary→backups) from a top-first list."""
	team = _resolve_team(team)
	from billing import payments

	return payments.reorder_payment_methods(team, ordered)
