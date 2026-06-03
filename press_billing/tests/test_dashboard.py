# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Customer dashboard endpoints + forecast (issues #26, #18)."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from press_billing import credits, dashboard, security
from press_billing.sync import receive_usage_events
from press_billing.tests.utils import make_plan

TEAM = "team-cust"
CLUSTER = "ap-south-1"
PLAN = "bundle-cust-test"


class TestDashboardSmoke(IntegrationTestCase):
	def test_whoami_returns_session_and_scope(self):
		out = dashboard.whoami()
		self.assertEqual(out["user"], frappe.session.user)
		self.assertIn("team", out)
		self.assertIn("is_billing_admin", out)

	def test_whoami_admin_flag_for_administrator(self):
		self.assertTrue(dashboard.whoami()["is_billing_admin"])


class CustomerDataBase(IntegrationTestCase):
	def setUp(self):
		make_plan(PLAN)
		self._purge()
		self.today = frappe.utils.getdate()
		self.month_start = frappe.utils.get_first_day(self.today)

	def tearDown(self):
		self._purge()

	def _purge(self):
		for dt in ("Invoice", "Price Lock", "Credit Ledger Entry"):
			frappe.db.delete(dt, {"team": TEAM})
		frappe.db.delete("Credit Wallet", {"team": TEAM})
		frappe.db.commit()

	def _provision(self, rate=3000):
		receive_usage_events(
			[{"event_id": "ev-cust", "team": TEAM, "resource_id": "srv-cust", "cluster": CLUSTER,
			  "plan": PLAN, "shown_rate": rate, "currency": "INR", "event_type": "subscribed",
			  "effective_from": f"{self.month_start} 00:00:00", "effective_to": None}]
		)


class TestForecast(CustomerDataBase):
	def test_forecast_projects_month_end_vs_credit(self):
		self._provision(rate=3000)  # active all month → full-month projection
		credits.purchase(TEAM, 1000, "INR")

		fc = dashboard.get_forecast(TEAM)
		self.assertEqual(fc["projected_total"], 3000.0)
		self.assertEqual(fc["credit_balance"], 1000.0)
		self.assertEqual(fc["shortfall"], 2000.0)
		self.assertGreaterEqual(fc["days_remaining"], 0)
		self.assertTrue(fc["line_items"])

	def test_forecast_no_runtime_is_zero(self):
		fc = dashboard.get_forecast(TEAM)
		self.assertEqual(fc["projected_total"], 0)
		self.assertEqual(fc["shortfall"], 0)


class TestCustomerReads(CustomerDataBase):
	def _invoice(self):
		return frappe.get_doc(
			{"doctype": "Invoice", "team": TEAM, "invoice_type": "billable", "status": "Paid",
			 "period_start": "2026-05-01", "period_end": "2026-05-31", "currency": "INR",
			 "subtotal": 1000, "output_tax_type": "GST", "output_tax_amount": 180, "total": 1180,
			 "amount_paid": 1180,
			 "items": [{"resource_type": "bundle", "plan": PLAN, "rate": 1000, "days": 30, "amount": 1000}]}
		).insert(ignore_permissions=True).name

	def test_list_invoices_is_summary_only(self):
		self._invoice()
		rows = dashboard.list_invoices(TEAM)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["status"], "Paid")
		self.assertEqual(rows[0]["total"], 1180)

	def test_get_invoice_returns_items_and_tax(self):
		inv = self._invoice()
		detail = dashboard.get_invoice(inv)
		self.assertEqual(detail["output_tax_type"], "GST")
		self.assertEqual(detail["output_tax_amount"], 180)
		self.assertEqual(len(detail["items"]), 1)

	def test_payment_methods_never_expose_secrets(self):
		from press_billing.tests.test_stripe_adapter import make_stripe_gateway

		gw = make_stripe_gateway("GW-Cust-Stripe").name
		frappe.get_doc(
			{"doctype": "Payment Method", "team": TEAM, "gateway": gw, "method_type": "card",
			 "status": "active", "display_label": "Visa ····4242", "gateway_method_id": "pm_secret",
			 "is_default": 1}
		).insert(ignore_permissions=True)
		rows = dashboard.list_payment_methods(TEAM)
		self.assertEqual(rows[0]["display_label"], "Visa ····4242")
		# Gateway handle / secrets are not in the customer payload.
		self.assertNotIn("gateway_method_id", rows[0])
		self.assertNotIn("api_key", rows[0])
		frappe.db.delete("Payment Method", {"team": TEAM})

	def test_credit_ledger_and_balance(self):
		credits.purchase(TEAM, 500, "INR")
		self.assertEqual(dashboard.get_credit_balance(TEAM)["balance"], 500)
		ledger = dashboard.credit_ledger(TEAM)
		self.assertEqual(ledger[0]["entry_type"], "credit")


class TestTeamScoping(CustomerDataBase):
	def test_customer_cannot_read_another_team(self):
		user = f"cust-{frappe.generate_hash(6)}@example.com"
		frappe.get_doc(
			{"doctype": "User", "email": user, "first_name": "Cust", "send_welcome_email": 0}
		).insert(ignore_permissions=True)
		frappe.set_user(user)
		try:
			with patch("press_billing.dashboard.get_user_team", return_value=TEAM), patch(
				"press_billing.security.get_user_team", return_value=TEAM
			):
				dashboard.list_invoices()  # own team — ok
				with self.assertRaises(frappe.PermissionError):
					dashboard.list_invoices("some-other-team")  # rejected, not widened
		finally:
			frappe.set_user("Administrator")
