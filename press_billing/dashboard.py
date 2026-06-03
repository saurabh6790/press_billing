# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Customer dashboard endpoints (#26 scaffold; data APIs land in #18)."""

import frappe

from press_billing.security import get_user_team, is_billing_admin


@frappe.whitelist()
def whoami() -> dict:
	"""Smoke endpoint: who the SPA is talking as, and their team scope."""
	return {
		"user": frappe.session.user,
		"team": get_user_team(),
		"is_billing_admin": is_billing_admin(),
	}
