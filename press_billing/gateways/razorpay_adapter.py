# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Razorpay GatewayAdapter.

One of two modules allowed to import a gateway SDK. Gateway knowledge (recurring
charge against a mandate token, refund, webhook signature + event shapes) is
ported from the working press implementation; the structure is the new adapter
model. The UPI Autopay mandate *lifecycle* (cap = trust tier) is issue #08.
"""

import razorpay
import requests

from press_billing.gateways.base import (
	GatewayAdapter,
	GatewayTimeout,
	NormalisedEvent,
	PaymentResult,
	RefundResult,
	header_value,
)

# Razorpay raises these for transient/server failures; declines are BadRequestError.
_TRANSIENT = (
	razorpay.errors.GatewayError,
	razorpay.errors.ServerError,
	requests.exceptions.RequestException,
)


class RazorpayAdapter(GatewayAdapter):
	def _client(self):
		return razorpay.Client(
			auth=(self.gateway.get_password("api_key"), self.gateway.get_password("api_secret"))
		)

	def charge(self, invoice, payment_method, idempotency_key: str) -> PaymentResult:
		"""Off-session recurring charge against a mandate token.

		An order carries the idempotency key as its (unique) receipt; the
		recurring payment is created against the token. Declines come back as a
		failed result; transient/network errors raise GatewayTimeout so a retry
		reuses the same receipt.
		"""
		client = self._client()
		amount_paise = int(round((invoice.amount or 0) * 100))
		currency = (invoice.currency or "").upper()
		try:
			order = client.order.create(
				{
					"amount": amount_paise,
					"currency": currency,
					"receipt": idempotency_key,
					"notes": {"invoice": invoice.get("name")},
				}
			)
			payment = client.payment.createRecurring(
				{
					"amount": amount_paise,
					"currency": currency,
					"order_id": order["id"],
					"customer_id": invoice.get("customer_id"),
					"token": payment_method.gateway_method_id,
					"recurring": "1",
				}
			)
		except razorpay.errors.BadRequestError as e:
			return PaymentResult(
				success=False,
				status="failed",
				failure_code=getattr(e, "code", None),
				failure_reason=str(e),
			)
		except _TRANSIENT as e:
			raise GatewayTimeout(str(e)) from e

		captured = payment.get("status") == "captured"
		return PaymentResult(
			success=captured,
			status="captured" if captured else payment.get("status"),
			gateway_transaction_id=payment.get("id"),
			raw=dict(payment),
		)

	def refund(self, payment_attempt, amount, reason: str) -> RefundResult:
		client = self._client()
		try:
			refund = client.payment.refund(
				payment_attempt.gateway_transaction_id,
				{"amount": int(round((amount or 0) * 100))},
			)
		except _TRANSIENT as e:
			raise GatewayTimeout(str(e)) from e

		done = refund.get("status") in ("processed", "pending")
		return RefundResult(
			success=done,
			status="completed" if done else refund.get("status"),
			gateway_refund_id=refund.get("id"),
			raw=dict(refund),
		)

	def verify_webhook_signature(self, payload: bytes, headers: dict) -> bool:
		"""HMAC-verify the raw webhook body. No DB writes; first security gate."""
		secret = self.gateway.get_password("webhook_secret")
		signature = header_value(headers, "X-Razorpay-Signature")
		body = payload.decode() if isinstance(payload, bytes) else payload
		try:
			self._client().utility.verify_webhook_signature(body, signature, secret)
			return True
		except razorpay.errors.SignatureVerificationError:
			return False

	def parse_webhook_event(self, payload: dict, headers: dict | None = None) -> NormalisedEvent:
		"""Razorpay carries the dedupe id in the X-Razorpay-Event-Id header."""
		return NormalisedEvent(
			gateway_event_id=header_value(headers, "X-Razorpay-Event-Id"),
			event_type=payload.get("event"),
			payload=payload,
		)

	def get_transaction_status(self, gateway_txn_id: str) -> str:
		return self._client().payment.fetch(gateway_txn_id).get("status")
