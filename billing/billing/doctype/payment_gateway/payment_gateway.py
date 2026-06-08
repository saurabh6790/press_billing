# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class PaymentGateway(Document):
	def get_adapter(self):
		"""Resolve the GatewayAdapter for this gateway (by adapter_key).

		Lives here so callers never need to know which gateway class is in play.
		"""
		from billing.gateways.registry import get_adapter

		return get_adapter(self)
