<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-lg font-semibold text-ink-gray-9">Payment Failures</h1>
      <p class="mt-0.5 text-sm text-ink-gray-6">Charge success rate by gateway and the failing attempts behind it.</p>
    </div>

    <!-- success rate per gateway -->
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div v-for="(g, name) in analytics.data?.by_gateway || {}" :key="name" class="rounded-xl border border-outline-gray-2 p-5">
        <p class="text-sm text-ink-gray-6">{{ name }}</p>
        <p class="mt-1 text-xl font-semibold" :class="g.success_rate >= 0.9 ? 'text-ink-green-3' : g.success_rate >= 0.6 ? 'text-ink-amber-3' : 'text-ink-red-3'">{{ (g.success_rate * 100).toFixed(0) }}%</p>
        <p class="mt-1 text-xs text-ink-gray-5">{{ g.captured }}/{{ g.total }} captured</p>
      </div>
      <div v-if="!Object.keys(analytics.data?.by_gateway || {}).length" class="text-sm text-ink-gray-5">No attempts recorded.</div>
    </div>

    <section>
      <h2 class="mb-2 text-base font-semibold text-ink-gray-9">Failed Attempts</h2>
      <div class="overflow-hidden rounded-lg border border-outline-gray-2">
        <table class="w-full text-sm">
          <thead><tr class="border-b border-outline-gray-2 bg-surface-gray-1 text-left text-ink-gray-5">
            <th class="px-4 py-2 font-normal">Team</th><th class="px-4 py-2 font-normal">Invoice</th>
            <th class="px-4 py-2 text-right font-normal">Amount</th><th class="px-4 py-2 font-normal">Gateway</th>
            <th class="px-4 py-2 font-normal">Reason</th><th class="px-4 py-2 font-normal">When</th>
          </tr></thead>
          <tbody>
            <tr v-for="f in failures.data || []" :key="f.name" class="border-b border-outline-gray-1 last:border-0">
              <td class="px-4 py-2 font-medium text-ink-gray-8">{{ f.team }}</td>
              <td class="px-4 py-2 text-ink-gray-7">{{ f.invoice }}</td>
              <td class="px-4 py-2 text-right text-ink-gray-8">{{ money(f.amount, f.currency) }}</td>
              <td class="px-4 py-2 text-ink-gray-7">{{ f.gateway }}</td>
              <td class="px-4 py-2 text-ink-red-4">{{ f.failure_reason || f.failure_code || '—' }}</td>
              <td class="px-4 py-2 text-ink-gray-6">{{ (f.creation || '').slice(0, 10) }}</td>
            </tr>
            <tr v-if="!(failures.data || []).length"><td colspan="6" class="px-4 py-8 text-center text-ink-gray-5">No failed payments. 🎉</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
<script setup>
import { createResource } from 'frappe-ui';
import { money } from '../utils';
const failures = createResource({ url: 'billing.api.admin.get_payment_failures', auto: true });
const analytics = createResource({ url: 'billing.api.admin.get_payment_analytics', auto: true });
</script>
