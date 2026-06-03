# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Dashboard endpoints (#26 scaffold smoke; customer APIs in #18)."""

import frappe
from frappe.tests import IntegrationTestCase

from press_billing import dashboard


class TestDashboardSmoke(IntegrationTestCase):
	def test_whoami_returns_session_and_scope(self):
		out = dashboard.whoami()
		self.assertEqual(out["user"], frappe.session.user)
		self.assertIn("team", out)
		self.assertIn("is_billing_admin", out)

	def test_whoami_admin_flag_for_administrator(self):
		# The test session runs as Administrator → billing admin.
		self.assertTrue(dashboard.whoami()["is_billing_admin"])
