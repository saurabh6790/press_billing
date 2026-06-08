<template>
  <div class="space-y-5">
    <div>
      <h1 class="text-lg font-semibold text-ink-gray-9">Payment History</h1>
      <p class="mt-0.5 text-sm text-ink-gray-6">Every charge against your card or mandate, including failed retries.</p>
    </div>

    <!-- suspended/past-due context banner: explains why a card-on-file team is blocked -->
    <div v-if="failedCount" class="rounded-md border border-outline-red-1 bg-surface-red-1 px-4 py-3 text-sm text-ink-red-4">
      {{ failedCount }} payment {{ failedCount === 1 ? 'attempt has' : 'attempts have' }} failed. A card on file does not guarantee a successful charge —
      please confirm your payment method is valid to restore service.
    </div>

    <div class="overflow-hidden rounded-lg border border-outline-gray-2">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-outline-gray-2 bg-surface-gray-1 text-left text-ink-gray-5">
            <th class="px-4 py-2.5 font-normal">Date</th>
            <th class="px-4 py-2.5 font-normal">Invoice</th>
            <th class="px-4 py-2.5 font-normal">Method</th>
            <th class="px-4 py-2.5 font-normal">Status</th>
            <th class="px-4 py-2.5 text-right font-normal">Amount</th>
            <th class="px-4 py-2.5 font-normal">Details</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in attempts.data || []" :key="a.name" class="border-b border-outline-gray-1 last:border-0 align-top">
            <td class="px-4 py-3 text-ink-gray-7 whitespace-nowrap">{{ (a.creation || '').slice(0, 10) }}</td>
            <td class="px-4 py-3 text-ink-gray-7">{{ a.invoice || '—' }}</td>
            <td class="px-4 py-3 text-ink-gray-7">{{ a.gateway || '—' }}</td>
            <td class="px-4 py-3">
              <Badge variant="subtle" :theme="attemptTheme(a.status)" :label="attemptLabel(a.status)" />
              <span v-if="a.retry_number" class="ml-1.5 text-xs text-ink-gray-5">retry {{ a.retry_number }}</span>
            </td>
            <td class="px-4 py-3 text-right text-ink-gray-8">{{ money(a.amount, a.currency) }}</td>
            <td class="px-4 py-3 text-ink-gray-6">
              <span v-if="a.status === 'failed'" class="text-ink-red-4">{{ a.failure_reason || a.failure_code || 'Declined' }}</span>
              <span v-else-if="a.gateway_transaction_id" class="font-mono text-xs text-ink-gray-5">{{ a.gateway_transaction_id }}</span>
              <span v-else>—</span>
            </td>
          </tr>
          <tr v-if="!(attempts.data || []).length">
            <td colspan="6" class="px-4 py-8 text-center text-ink-gray-5">No payment attempts yet.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
<script setup>
import { computed, watch } from 'vue';
import { Badge, createResource } from 'frappe-ui';
import { store } from '../store';
import { money, attemptLabel, attemptTheme } from '../utils';
const attempts = createResource({ url: 'billing.api.dashboard.list_payment_attempts', makeParams: () => ({ team: store.team }) });
watch(() => store.team, (t) => t && attempts.reload(), { immediate: true });
const failedCount = computed(() => (attempts.data || []).filter((a) => a.status === 'failed').length);
</script>
