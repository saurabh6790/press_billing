# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Stripe GatewayAdapter.

The only module that imports the `stripe` SDK. Gateway knowledge (Payment
Intents, refunds, webhook signature verification) is ported from the working
press implementation; the structure is the new adapter model.
"""

import stripe

from press_billing.gateways.base import (
	GatewayAdapter,
	GatewayTimeout,
	NormalisedEvent,
	PaymentResult,
	RefundResult,
	header_value,
)


class StripeAdapter(GatewayAdapter):
	def _configure(self):
		stripe.api_key = self.gateway.get_password("api_secret")
		# https://docs.stripe.com/rate-limits#object-lock-timeouts
		stripe.max_network_retries = 2
		return stripe

	def charge(self, invoice, payment_method, idempotency_key: str) -> PaymentResult:
		"""Off-session charge of a stored payment method. Idempotent per attempt.

		Declines are returned as a failed PaymentResult (normal billing flow);
		network/timeouts raise GatewayTimeout so the caller retries with the
		SAME idempotency key (Stripe dedupes), never double-charging.
		"""
		self._configure()
		amount_minor = int(round((invoice.amount or 0) * 100))
		try:
			intent = stripe.PaymentIntent.create(
				amount=amount_minor,
				currency=(invoice.currency or "").lower(),
				customer=invoice.get("customer_id"),
				payment_method=payment_method.gateway_method_id,
				off_session=True,
				confirm=True,
				idempotency_key=idempotency_key,
			)
		except stripe.error.CardError as e:
			return PaymentResult(
				success=False,
				status="failed",
				failure_code=getattr(e, "code", None),
				failure_reason=getattr(e, "user_message", None) or str(e),
				raw=getattr(e, "json_body", None) or {},
			)
		except (stripe.error.APIConnectionError, stripe.error.RateLimitError) as e:
			raise GatewayTimeout(str(e)) from e

		succeeded = intent.get("status") == "succeeded"
		return PaymentResult(
			success=succeeded,
			status="captured" if succeeded else intent.get("status"),
			gateway_transaction_id=intent.get("id"),
			raw=dict(intent),
		)

	def refund(self, payment_attempt, amount, reason: str) -> RefundResult:
		"""Refund a captured charge to source. Symmetric across gateways."""
		self._configure()
		try:
			refund = stripe.Refund.create(
				payment_intent=payment_attempt.gateway_transaction_id,
				amount=int(round((amount or 0) * 100)),
			)
		except (stripe.error.APIConnectionError, stripe.error.RateLimitError) as e:
			raise GatewayTimeout(str(e)) from e

		completed = refund.get("status") in ("succeeded", "pending")
		return RefundResult(
			success=completed,
			status="completed" if completed else refund.get("status"),
			gateway_refund_id=refund.get("id"),
			raw=dict(refund),
		)

	def verify_webhook_signature(self, payload: bytes, headers: dict) -> bool:
		"""HMAC-verify the raw webhook body. No DB writes; first security gate."""
		secret = self.gateway.get_password("webhook_secret")
		signature = header_value(headers, "Stripe-Signature")
		try:
			stripe.Webhook.construct_event(payload, signature, secret)
			return True
		except (ValueError, stripe.error.SignatureVerificationError):
			return False

	def parse_webhook_event(self, payload: dict, headers: dict | None = None) -> NormalisedEvent:
		"""Normalise an already-verified Stripe event dict (id is in the body)."""
		return NormalisedEvent(
			gateway_event_id=payload.get("id"),
			event_type=payload.get("type"),
			payload=payload,
		)

	def get_transaction_status(self, gateway_txn_id: str) -> str:
		self._configure()
		intent = stripe.PaymentIntent.retrieve(gateway_txn_id)
		return intent.get("status")
