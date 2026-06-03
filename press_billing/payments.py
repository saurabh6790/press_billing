# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Card Payment Method lifecycle (issue #05).

Adding a card is a two-step, gateway-mediated flow: the customer initiates
setup (Stripe SetupIntent -> client secret), confirms with the card on the
frontend, and the method is proven live by a **micro-charge captured and
immediately refunded** before it becomes `active`. A method is never trusted on
the API response alone.

    pending_validation --(micro-charge ok)--> active --(monthly expiry)--> expired
                       \--(micro-charge fail)--> failed

Cards are off-session and have no mandate ceiling (that is the UPI Autopay path,
see mandates.py). This module never imports a gateway SDK — it resolves the
adapter through the registry, keeping the gateway seam intact.
"""

import frappe

CARD_METHOD = "card"


def _adapter(gateway: str):
	from press_billing.gateways.registry import get_adapter

	return get_adapter(frappe.get_doc("Payment Gateway", gateway))


@frappe.whitelist()
def initiate_payment_method_setup(team: str, gateway: str, gateway_customer_id: str | None = None) -> dict:
	"""Begin adding a card: open a SetupIntent and a pending Payment Method.

	Returns the client secret the frontend confirms the card against. No money
	moves here and the method is not yet usable.
	"""
	handles = _adapter(gateway).setup_payment_method(team, {"customer_id": gateway_customer_id})

	method = frappe.get_doc(
		{
			"doctype": "Payment Method",
			"team": team,
			"gateway": gateway,
			"method_type": CARD_METHOD,
			"status": "pending_validation",
			"gateway_customer_id": gateway_customer_id,
			"setup_reference": handles.get("setup_intent_id"),
		}
	).insert(ignore_permissions=True)

	return {**handles, "payment_method": method.name}


@frappe.whitelist()
def confirm_payment_method(
	payment_method: str,
	gateway_method_id: str,
	display_label: str | None = None,
	expiry_month: int | None = None,
	expiry_year: int | None = None,
	gateway_customer_id: str | None = None,
) -> dict:
	"""Confirm a card the customer authorised on the frontend.

	Stores the gateway method handle, then runs the micro-charge + auto-refund
	validation. The method becomes `active` only on a successful micro-charge;
	a failure (or decline) leaves it `failed`. The first active method for a
	team becomes its default.
	"""
	method = frappe.get_doc("Payment Method", payment_method)
	method.gateway_method_id = gateway_method_id
	if gateway_customer_id:
		method.gateway_customer_id = gateway_customer_id
	if display_label:
		method.display_label = display_label
	if expiry_month:
		method.expiry_month = expiry_month
	if expiry_year:
		method.expiry_year = expiry_year
	method.save(ignore_permissions=True)

	if not _adapter(method.gateway).validate_payment_method(method):
		method.status = "failed"
		method.save(ignore_permissions=True)
		return method

	method.status = "active"
	method.validated_at = frappe.utils.now_datetime()
	method.save(ignore_permissions=True)
	_ensure_one_default(method)
	return method


def _ensure_one_default(method):
	"""A team's first active method becomes its default — never zero, never two."""
	other_default = frappe.get_all(
		"Payment Method",
		filters={
			"team": method.team,
			"is_default": 1,
			"status": "active",
			"name": ["!=", method.name],
		},
		limit=1,
	)
	if not other_default and not method.is_default:
		frappe.db.set_value("Payment Method", method.name, "is_default", 1)
		method.is_default = 1


@frappe.whitelist()
def set_default_payment_method(payment_method: str):
	"""Make this the team's sole default. Only an active method can be default."""
	method = frappe.get_doc("Payment Method", payment_method)
	if method.status != "active":
		frappe.throw("Only an active payment method can be the default.", frappe.ValidationError)

	for name in frappe.get_all(
		"Payment Method",
		filters={"team": method.team, "is_default": 1, "name": ["!=", method.name]},
		pluck="name",
	):
		frappe.db.set_value("Payment Method", name, "is_default", 0)
	frappe.db.set_value("Payment Method", method.name, "is_default", 1)
	return frappe.get_doc("Payment Method", method.name)


@frappe.whitelist()
def delete_payment_method(payment_method: str) -> dict:
	"""Remove a payment method. If it was the team's default, promote the next
	active method so the team keeps exactly one default (or none if it was the
	last)."""
	method = frappe.get_doc("Payment Method", payment_method)
	team, was_default = method.team, method.is_default
	frappe.delete_doc("Payment Method", method.name, ignore_permissions=True)

	promoted = None
	if was_default:
		candidates = frappe.get_all(
			"Payment Method",
			filters={"team": team, "status": "active"},
			order_by="creation asc",
			limit=1,
			pluck="name",
		)
		if candidates:
			promoted = candidates[0]
			frappe.db.set_value("Payment Method", promoted, "is_default", 1)
	return {"deleted": payment_method, "new_default": promoted}


def expire_payment_methods(now=None) -> dict:
	"""Monthly scheduler: flip cards past their expiry month to `expired`.

	A card is valid through the end of its printed expiry month; the day after,
	it is no longer chargeable.
	"""
	from press_billing import notifications

	today = frappe.utils.getdate(now or frappe.utils.now_datetime())
	expired = []
	for m in frappe.get_all(
		"Payment Method",
		filters={"method_type": CARD_METHOD, "status": "active"},
		fields=["name", "team", "display_label", "expiry_month", "expiry_year"],
	):
		if not m.expiry_year or not m.expiry_month:
			continue
		month_start = frappe.utils.getdate(f"{int(m.expiry_year):04d}-{int(m.expiry_month):02d}-01")
		if frappe.utils.get_last_day(month_start) < today:
			frappe.db.set_value("Payment Method", m.name, "status", "expired")
			expired.append(m.name)
			notifications.notify(
				m.team, "card_expiry", context={"label": m.display_label or "card"},
				reference_doctype="Payment Method", reference_name=m.name,
			)
	return {"expired": expired}
