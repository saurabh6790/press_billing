# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Server context for the billing SPA shell (#26)."""

no_cache = 1


def get_context(context):
	# Standalone SPA page — skip the website sidebar/header chrome.
	context.no_header = True
	context.no_breadcrumbs = True
	return context
