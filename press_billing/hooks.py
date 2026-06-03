app_name = "press_billing"
app_title = "Press Billing"
app_publisher = "Frappe"
app_description = "Billing & payments system of record for Frappe Cloud v2"
app_email = "saurabh6790@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "press_billing",
# 		"logo": "/assets/press_billing/logo.png",
# 		"title": "Press Billing",
# 		"route": "/press_billing",
# 		"has_permission": "press_billing.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/press_billing/css/press_billing.css"
# app_include_js = "/assets/press_billing/js/press_billing.js"

# include js, css files in header of web template
# web_include_css = "/assets/press_billing/css/press_billing.css"
# web_include_js = "/assets/press_billing/js/press_billing.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "press_billing/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "press_billing/public/icons.svg"

# Home Pages
# ----------

# The billing SPA (#26): deep links under /billing/* are served by the same
# www/billing.html shell so the client-side router can take over.
website_route_rules = [
	{"from_route": "/billing/<path:app_path>", "to_route": "billing"},
]

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "press_billing.utils.jinja_methods",
# 	"filters": "press_billing.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "press_billing.install.before_install"
# after_install = "press_billing.install.after_install"

# Ensure billing roles (#22) + the User->team link field exist after migrate.
after_migrate = [
	"press_billing.security.ensure_billing_roles",
	"press_billing.dashboard.ensure_billing_team_field",
]

# Uninstallation
# ------------

# before_uninstall = "press_billing.uninstall.before_uninstall"
# after_uninstall = "press_billing.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "press_billing.utils.before_app_install"
# after_app_install = "press_billing.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "press_billing.utils.before_app_uninstall"
# after_app_uninstall = "press_billing.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "press_billing.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
	# Retry/dunning + staged suspension for unpaid invoices, and ERPNext sync
	# retries whose backoff window has elapsed.
	"daily": [
		"press_billing.dunning.run_dunning",
		"press_billing.reconciliation.run_reconciliation",
	],
	"hourly": [
		"press_billing.erpnext_sync.retry_failed_syncs",
	],
	# Cards expire at the end of their printed month; flip lapsed ones monthly.
	"monthly": [
		"press_billing.payments.expire_payment_methods",
	],
}

# Testing
# -------

# before_tests = "press_billing.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "press_billing.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "press_billing.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["press_billing.utils.before_request"]
# after_request = ["press_billing.utils.after_request"]

# Job Events
# ----------
# before_job = ["press_billing.utils.before_job"]
# after_job = ["press_billing.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"press_billing.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

