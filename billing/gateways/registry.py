# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Resolve a Payment Gateway config row to its GatewayAdapter implementation."""

import frappe

from billing.gateways.base import GatewayAdapter


def get_adapter(gateway) -> GatewayAdapter:
	"""Return the adapter instance for a Payment Gateway doc, keyed by adapter_key."""
	from billing.gateways.paypal_adapter import PayPalAdapter
	from billing.gateways.razorpay_adapter import RazorpayAdapter
	from billing.gateways.stripe_adapter import StripeAdapter

	adapters = {
		"stripe": StripeAdapter,
		"razorpay": RazorpayAdapter,
		"paypal": PayPalAdapter,
	}

	adapter_class = adapters.get(gateway.adapter_key)
	if not adapter_class:
		frappe.throw(f"No GatewayAdapter registered for adapter_key '{gateway.adapter_key}'")

	return adapter_class(gateway)
