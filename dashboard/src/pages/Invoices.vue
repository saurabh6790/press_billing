<template>
  <div class="space-y-4">
    <h1 class="text-xl font-semibold">Invoices</h1>
    <div class="overflow-hidden rounded-lg border border-gray-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-gray-500">
          <tr><th class="px-4 py-2">Invoice</th><th class="px-4 py-2">Period</th><th class="px-4 py-2">Total</th><th class="px-4 py-2">Status</th></tr>
        </thead>
        <tbody>
          <tr v-for="inv in invoices.data || []" :key="inv.name" class="border-t border-gray-100">
            <td class="px-4 py-2 font-medium">{{ inv.name }}</td>
            <td class="px-4 py-2">{{ inv.period_start }} → {{ inv.period_end }}</td>
            <td class="px-4 py-2">{{ money(inv.total) }}</td>
            <td class="px-4 py-2"><Badge :theme="statusTheme(inv.status)" :label="inv.status" /></td>
          </tr>
          <tr v-if="!(invoices.data || []).length"><td colspan="4" class="px-4 py-4 text-gray-500">No invoices yet.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
<script setup>
import { Badge, createResource } from 'frappe-ui';
const invoices = createResource({ url: 'press_billing.dashboard.list_invoices', auto: true });
const money = (v) => '₹ ' + Number(v || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 });
const statusTheme = (s) => ({ Paid: 'green', Open: 'blue', Overdue: 'red', Draft: 'gray', Cancelled: 'gray', Waived: 'amber' }[s] || 'gray');
</script>
