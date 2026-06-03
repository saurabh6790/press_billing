<template>
  <div class="space-y-6">
    <h1 class="text-xl font-semibold">Billing Overview</h1>
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div class="rounded-lg border border-gray-200 bg-white p-5">
        <p class="text-sm text-gray-500">This month (projected)</p>
        <p class="mt-1 text-2xl font-semibold">{{ money(forecast.data?.projected_total) }}</p>
        <p class="mt-1 text-xs text-gray-500">{{ forecast.data?.days_remaining ?? '–' }} days remaining</p>
      </div>
      <div class="rounded-lg border border-gray-200 bg-white p-5">
        <p class="text-sm text-gray-500">Credit balance</p>
        <p class="mt-1 text-2xl font-semibold">{{ money(forecast.data?.credit_balance) }}</p>
      </div>
      <div class="rounded-lg border border-gray-200 bg-white p-5">
        <p class="text-sm text-gray-500">Projected shortfall</p>
        <p class="mt-1 text-2xl font-semibold" :class="shortfallClass">{{ money(forecast.data?.shortfall) }}</p>
      </div>
    </div>
    <div>
      <h2 class="mb-2 text-base font-medium">Active subscriptions</h2>
      <div class="overflow-hidden rounded-lg border border-gray-200 bg-white">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-left text-gray-500">
            <tr><th class="px-4 py-2">Plan</th><th class="px-4 py-2">Cluster</th><th class="px-4 py-2">Standing</th></tr>
          </thead>
          <tbody>
            <tr v-for="s in subscriptions.data || []" :key="s.name" class="border-t border-gray-100">
              <td class="px-4 py-2">{{ s.plan }}</td>
              <td class="px-4 py-2">{{ s.cluster }}</td>
              <td class="px-4 py-2"><Badge :theme="standingTheme(s.account_standing)" :label="s.account_standing" /></td>
            </tr>
            <tr v-if="!(subscriptions.data || []).length"><td colspan="3" class="px-4 py-4 text-gray-500">No active subscriptions.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
<script setup>
import { computed } from 'vue';
import { Badge, createResource } from 'frappe-ui';
const forecast = createResource({ url: 'press_billing.dashboard.get_forecast', auto: true });
const subscriptions = createResource({ url: 'press_billing.dashboard.list_subscriptions', auto: true });
const money = (v) => '₹ ' + Number(v || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 });
const shortfallClass = computed(() => (forecast.data?.shortfall > 0 ? 'text-amber-600' : 'text-green-600'));
const standingTheme = (s) => ({ current: 'green', past_due: 'amber', suspended: 'red' }[s] || 'gray');
</script>
