import { createResource } from 'frappe-ui';

// Thin wrappers over the whitelisted billing endpoints. The server enforces
// team-scoping (require_team_access) — the client never passes a team it
// shouldn't see.
export function forecastResource() {
  return createResource({ url: 'billing.dashboard.get_forecast', auto: true });
}

export function invoicesResource() {
  return createResource({ url: 'billing.dashboard.list_invoices', auto: true });
}

export function paymentMethodsResource() {
  return createResource({ url: 'billing.dashboard.list_payment_methods', auto: true });
}

export function creditLedgerResource() {
  return createResource({ url: 'billing.dashboard.credit_ledger', auto: true });
}
