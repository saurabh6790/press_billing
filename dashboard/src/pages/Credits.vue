<template>
  <div class="space-y-4">
    <h1 class="text-xl font-semibold">Credits</h1>
    <div class="rounded-lg border border-gray-200 bg-white p-5">
      <p class="text-sm text-gray-500">Wallet balance</p>
      <p class="mt-1 text-2xl font-semibold">{{ money(balance.data?.balance) }}</p>
    </div>
    <div class="overflow-hidden rounded-lg border border-gray-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-gray-500">
          <tr><th class="px-4 py-2">Type</th><th class="px-4 py-2">Amount</th><th class="px-4 py-2">Balance</th><th class="px-4 py-2">Note</th></tr>
        </thead>
        <tbody>
          <tr v-for="(e, i) in ledger.data || []" :key="i" class="border-t border-gray-100">
            <td class="px-4 py-2"><Badge :theme="e.entry_type === 'credit' ? 'green' : 'amber'" :label="e.entry_type" /></td>
            <td class="px-4 py-2">{{ money(e.amount) }}</td>
            <td class="px-4 py-2">{{ money(e.running_balance) }}</td>
            <td class="px-4 py-2 text-gray-500">{{ e.note }}</td>
          </tr>
          <tr v-if="!(ledger.data || []).length"><td colspan="4" class="px-4 py-4 text-gray-500">No credit activity.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
<script setup>
import { Badge, createResource } from 'frappe-ui';
const balance = createResource({ url: 'press_billing.dashboard.get_credit_balance', auto: true });
const ledger = createResource({ url: 'press_billing.dashboard.credit_ledger', auto: true });
const money = (v) => '₹ ' + Number(v || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 });
</script>
