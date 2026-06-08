# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from billing.tests.test_stripe_adapter import make_stripe_gateway


class TestPaymentGatewaySecrets(IntegrationTestCase):
	def test_secrets_are_encrypted_at_rest_but_recoverable(self):
		gw = make_stripe_gateway()

		# Recoverable by the adapter via get_password...
		self.assertEqual(gw.get_password("webhook_secret"), "whsec_test_123")

		# ...but never stored in plaintext.
		stored = frappe.db.get_value("Payment Gateway", gw.name, "webhook_secret")
		self.assertNotEqual(stored, "whsec_test_123")

	def test_password_fields_are_not_exposed_in_document_dict(self):
		gw = make_stripe_gateway()
		# Password fieldtype values are not serialised as plaintext in as_dict.
		self.assertNotEqual(gw.as_dict().get("api_secret"), "sk_test_123")


class TestGatewayCredentialResolution(IntegrationTestCase):
	"""GatewayAdapter.get_credential lets live keys live in common_site_config.json
	(overriding the Payment Gateway doc) while falling back to the doc otherwise."""

	def test_falls_back_to_doc_when_not_in_site_config(self):
		from billing.gateways.registry import get_adapter

		gw = make_stripe_gateway("GW-Cred-Test")
		adapter = get_adapter(gw)
		# stripe_webhook_secret is not in this site's config -> read off the doc.
		self.assertNotIn("stripe_webhook_secret", frappe.conf)
		self.assertEqual(adapter.get_credential("webhook_secret"), "whsec_test_123")

	def test_site_config_key_overrides_the_doc(self):
		from billing.gateways.registry import get_adapter

		gw = make_stripe_gateway("GW-Cred-Test2")
		adapter = get_adapter(gw)
		with patch.dict(frappe.local.conf, {"stripe_webhook_secret": "whsec_from_conf"}):
			self.assertEqual(adapter.get_credential("webhook_secret"), "whsec_from_conf")
		# Override gone -> doc value again.
		self.assertEqual(adapter.get_credential("webhook_secret"), "whsec_test_123")
