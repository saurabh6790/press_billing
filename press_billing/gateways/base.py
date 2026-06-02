# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""GatewayAdapter — the single seam between core billing and payment gateways.

Core billing never imports a gateway SDK. Each gateway implements this
interface; adding a gateway is one subclass passing the shared contract suite.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


def header_value(headers: dict, name: str):
	"""Case-insensitive header lookup (werkzeug preserves sent casing)."""
	if not headers:
		return None
	target = name.lower()
	for key, value in headers.items():
		if key.lower() == target:
			return value
	return None


@dataclass
class PaymentResult:
	success: bool
	status: str  # captured / authorised / failed
	gateway_transaction_id: str | None = None
	failure_code: str | None = None
	failure_reason: str | None = None
	raw: dict = field(default_factory=dict)


@dataclass
class RefundResult:
	success: bool
	status: str  # completed / failed
	gateway_refund_id: str | None = None
	raw: dict = field(default_factory=dict)


@dataclass
class NormalisedEvent:
	gateway_event_id: str
	event_type: str
	payload: dict = field(default_factory=dict)


class GatewayError(Exception):
	"""Generic gateway failure that is not a clean decline."""


class GatewayTimeout(GatewayError):
	"""Network/timeout failure. Retry MUST reuse the same idempotency key."""


class GatewayAdapter(ABC):
	"""One instance per Payment Gateway config row."""

	def __init__(self, gateway):
		self.gateway = gateway

	@abstractmethod
	def charge(self, invoice, payment_method, idempotency_key: str) -> PaymentResult: ...

	@abstractmethod
	def refund(self, payment_attempt, amount, reason: str) -> RefundResult: ...

	@abstractmethod
	def verify_webhook_signature(self, payload: bytes, headers: dict) -> bool: ...

	@abstractmethod
	def parse_webhook_event(self, payload: dict, headers: dict | None = None) -> NormalisedEvent: ...

	@abstractmethod
	def get_transaction_status(self, gateway_txn_id: str) -> str: ...
