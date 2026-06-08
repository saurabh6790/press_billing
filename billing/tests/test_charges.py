# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Charge invoice -> Payment Attempt -> webhook -> Paid (issue #10)."""

import json
import threading
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from billing import charges, subscriptions, webhooks
from billing.gateways.base import PaymentResult
from billing.tests.test_stripe_adapter import make_stripe_gateway
from billing.tests.utils import make_plan

TEAM = "team-charge"
CLUSTER = "ap-south-1"
PLAN = "bundle-charge-test"
GATEWAY = "GW-Test-Stripe"


def run_workers(n, fn):
	site = frappe.local.site
	results = {}

	def worker(i):
		frappe.init(site=site)
		frappe.connect()
		frappe.set_user("Administrator")
		try:
			results[i] = fn(i)
			frappe.db.commit()
		except Exception as e:  # noqa: BLE001
			frappe.db.rollback()
			results[i] = type(e).__name__
		finally:
			frappe.destroy()

	threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
	for t in threads:
		t.start()
	for t in threads:
		t.join()
	return results


@contextmanager
def stub_adapter(success=True, txn_id="pi_x"):
	adapter = MagicMock()
	adapter.charge.return_value = PaymentResult(
		success=success,
		status="captured" if success else "failed",
		gateway_transaction_id=txn_id if success else None,
		failure_code=None if success else "card_declined",
		failure_reason=None if success else "declined",
	)
	with patch("billing.gateways.registry.get_adapter", return_value=adapter):
		yield adapter


class ChargeTestBase(IntegrationTestCase):
	def setUp(self):
		make_plan(PLAN)
		make_stripe_gateway(GATEWAY)
		self._purge()
		self.method = self._active_card()
		self.sub = subscriptions.create_subscription(
			team=TEAM,
			cluster=CLUSTER,
			plan=PLAN,
			billing_cycle="monthly",
			default_payment_method=self.method,
			gateway=GATEWAY,
		).name

	def tearDown(self):
		self._purge()

	def _purge(self):
		for dt in ("Payment Attempt", "Invoice"):
			frappe.db.delete(dt, {"team": TEAM})
		for pm in frappe.get_all("Payment Method", {"team": TEAM}, pluck="name"):
			frappe.db.delete("Payment Method", {"name": pm})
		for we in frappe.get_all("Webhook Event", pluck="name"):
			frappe.db.delete("Webhook Event", {"name": we})
		for sub in frappe.get_all("Subscription", {"team": TEAM}, pluck="name"):
			frappe.db.delete("Subscription Change", {"subscription": sub})
			frappe.db.delete("Subscription", {"name": sub})
		frappe.db.commit()

	def _active_card(self):
		return frappe.get_doc(
			{
				"doctype": "Payment Method",
				"team": TEAM,
				"gateway": GATEWAY,
				"method_type": "card",
				"status": "active",
				"gateway_method_id": "pm_card",
				"gateway_customer_id": "cus_1",
				"is_default": 1,
			}
		).insert(ignore_permissions=True).name

	def _open_invoice(self, total=1000):
		return frappe.get_doc(
			{
				"doctype": "Invoice",
				"team": TEAM,
				"subscription": self.sub,
				"status": "Open",
				"period_start": "2026-06-01",
				"period_end": "2026-06-30",
				"currency": "INR",
				"subtotal": total,
				"total": total,
				"credit_applied": 0,
				"expected_collection": total,
				"amount_paid": 0,
			}
		).insert(ignore_permissions=True).name

	def _stripe_event(self, gateway_event_id, event_type, txn_id):
		payload = {"id": gateway_event_id, "type": event_type, "data": {"object": {"id": txn_id}}}
		return frappe.get_doc(
			{
				"doctype": "Webhook Event",
				"gateway": GATEWAY,
				"gateway_event_id": gateway_event_id,
				"event_type": event_type,
				"raw_payload": json.dumps(payload),
				"status": "received",
			}
		).insert(ignore_permissions=True).name


class TestChargeInvoice(ChargeTestBase):
	def test_charge_creates_attempt_but_does_not_mark_paid(self):
		inv = self._open_invoice(1000)
		with stub_adapter(success=True, txn_id="pi_1") as adapter:
			result = charges.pay_invoice(inv)

		adapter.charge.assert_called_once()
		# Idempotency key handed to the gateway is the attempt's own name.
		attempt = frappe.get_doc("Payment Attempt", result["attempt"])
		self.assertEqual(adapter.charge.call_args.args[2], attempt.idempotency_key)
		self.assertEqual(attempt.idempotency_key, attempt.name)
		self.assertEqual(attempt.status, "captured")
		self.assertEqual(attempt.gateway_transaction_id, "pi_1")
		# Crucially: invoice is NOT Paid on the charge response.
		self.assertEqual(frappe.db.get_value("Invoice", inv, "status"), "Open")

	def test_declined_charge_records_failed_attempt(self):
		inv = self._open_invoice(1000)
		with stub_adapter(success=False):
			result = charges.pay_invoice(inv)
		self.assertFalse(result["charged"])
		attempt = frappe.get_doc("Payment Attempt", result["attempt"])
		self.assertEqual(attempt.status, "failed")
		self.assertEqual(attempt.failure_code, "card_declined")
		self.assertEqual(frappe.db.get_value("Invoice", inv, "status"), "Open")

	def test_webhook_settles_invoice_to_paid(self):
		inv = self._open_invoice(1000)
		with stub_adapter(success=True, txn_id="pi_settle"):
			charges.pay_invoice(inv)

		event = self._stripe_event("evt_1", "payment_intent.succeeded", "pi_settle")
		out = charges.apply_webhook(event)

		self.assertEqual(out["result"], "paid")
		invoice = frappe.get_doc("Invoice", inv)
		self.assertEqual(invoice.status, "Paid")
		self.assertEqual(invoice.amount_paid, 1000.0)
		# Notification logged (the #20 suite is the real sender).
		comments = frappe.get_all(
			"Comment", {"reference_doctype": "Invoice", "reference_name": inv, "comment_type": "Info"}
		)
		self.assertTrue(comments)

	def test_duplicate_success_webhook_is_idempotent(self):
		inv = self._open_invoice(1000)
		with stub_adapter(success=True, txn_id="pi_dup"):
			charges.pay_invoice(inv)
		e1 = self._stripe_event("evt_1", "payment_intent.succeeded", "pi_dup")
		e2 = self._stripe_event("evt_2", "payment_intent.succeeded", "pi_dup")

		charges.apply_webhook(e1)
		second = charges.apply_webhook(e2)
		self.assertFalse(second["settled"])  # already settled, no double-apply
		self.assertEqual(frappe.db.get_value("Invoice", inv, "amount_paid"), 1000.0)

	def test_failure_webhook_leaves_invoice_open(self):
		inv = self._open_invoice(1000)
		with stub_adapter(success=True, txn_id="pi_fail"):
			charges.pay_invoice(inv)
		event = self._stripe_event("evt_f", "payment_intent.payment_failed", "pi_fail")
		charges.apply_webhook(event)
		self.assertEqual(frappe.db.get_value("Invoice", inv, "status"), "Open")


class TestConcurrentPay(ChargeTestBase):
	def test_concurrent_pay_invoice_makes_one_captured_attempt(self):
		inv = self._open_invoice(1000)
		frappe.db.commit()

		with stub_adapter(success=True, txn_id="pi_once"):
			results = run_workers(10, lambda i: charges.pay_invoice(inv).get("reason", "charged"))

		frappe.db.rollback()
		attempts = frappe.get_all("Payment Attempt", {"invoice": inv}, ["name", "status"])
		self.assertEqual(len(attempts), 1)  # exactly one attempt created
		self.assertEqual(attempts[0].status, "captured")  # and only it reaches captured


class TestFullStripeCycle(ChargeTestBase):
	def test_open_charge_webhook_paid(self):
		import stripe

		from billing.gateways.stripe_adapter import StripeAdapter

		inv = self._open_invoice(1000)

		# Charge through the REAL StripeAdapter with only the SDK call stubbed.
		with patch.object(
			stripe.PaymentIntent, "create", return_value={"id": "pi_cycle", "status": "succeeded"}
		):
			charges.pay_invoice(inv)
		self.assertEqual(frappe.db.get_value("Invoice", inv, "status"), "Open")  # not paid yet

		# Deliver the webhook through the signature-first receiver, then handle it.
		body = json.dumps(
			{"id": "evt_cycle", "type": "payment_intent.succeeded", "data": {"object": {"id": "pi_cycle"}}}
		).encode()
		with patch.object(StripeAdapter, "verify_webhook_signature", return_value=True):
			webhooks.process_webhook("stripe", body, {"Stripe-Signature": "x"})

		event_name = frappe.get_all("Webhook Event", {"gateway_event_id": "evt_cycle"}, pluck="name")[0]
		webhooks.handle_webhook_event(event_name)

		invoice = frappe.get_doc("Invoice", inv)
		self.assertEqual(invoice.status, "Paid")
		self.assertEqual(invoice.amount_paid, 1000.0)
