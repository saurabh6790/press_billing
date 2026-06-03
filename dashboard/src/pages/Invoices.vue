<template>
  <div class="space-y-4">
    <h1 class="text-xl font-semibold text-ink-gray-9">Invoices</h1>
    <div class="overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white">
      <table class="w-full text-sm">
        <thead class="bg-surface-gray-2 text-left text-ink-gray-5">
          <tr><th class="px-4 py-2 font-medium">Invoice</th><th class="px-4 py-2 font-medium">Period</th><th class="px-4 py-2 font-medium">Total</th><th class="px-4 py-2 font-medium">Status</th></tr>
        </thead>
        <tbody>
          <tr v-for="inv in invoices.data || []" :key="inv.name" class="border-t border-outline-gray-1">
            <td class="px-4 py-2 font-medium text-ink-gray-8">{{ inv.name }}</td>
            <td class="px-4 py-2 text-ink-gray-7">{{ inv.period_start }} → {{ inv.period_end }}</td>
            <td class="px-4 py-2 text-ink-gray-8">{{ money(inv.total) }}</td>
            <td class="px-4 py-2"><Badge variant="subtle" :theme="statusTheme(inv.status)" :label="inv.status" /></td>
          </tr>
          <tr v-if="!(invoices.data || []).length"><td colspan="4" class="px-4 py-4 text-ink-gray-5">No invoices yet.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
<script setup>
import { Badge, createResource } from 'frappe-ui';
import { money, statusTheme } from '../utils';
const invoices = createResource({ url: 'press_billing.dashboard.list_invoices', auto: true });
</script>
