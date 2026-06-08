# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Server context for the billing SPA shell (#26).

Reads the Vite-built index.html and surfaces its (content-hashed) asset URLs to
the template, so a fresh build is always served — no stale-cache mismatches.
"""

import os
import re

import frappe

no_cache = 1


def get_context(context):
	context.no_header = True
	context.no_breadcrumbs = True
	context.css_files = []
	context.js_files = []
	index = os.path.join(
		frappe.get_app_path("billing"), "public", "dashboard", "index.html"
	)
	if os.path.exists(index):
		with open(index, encoding="utf-8") as f:
			html = f.read()
		context.css_files = re.findall(r'href="([^"]+\.css)"', html)
		context.js_files = re.findall(r'src="([^"]+\.js)"', html)
	return context
