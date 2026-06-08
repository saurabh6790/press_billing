<template>
  <div>
    <table class="w-full text-sm">
      <thead><tr class="border-b border-outline-gray-2 text-left text-ink-gray-5">
        <th class="py-2.5 pr-4 font-normal">Invoice</th><th class="py-2.5 pr-4 font-normal">Status</th>
        <th class="py-2.5 pr-4 font-normal">Period</th><th class="py-2.5 pr-4 text-right font-normal">Total</th>
        <th class="py-2.5 pr-4 text-right font-normal">Paid</th><th class="py-2.5 pr-4 text-right font-normal">Due</th><th></th>
      </tr></thead>
      <tbody>
        <tr v-for="row in invoices.data || []" :key="row.name" class="cursor-pointer border-b border-outline-gray-1 hover:bg-surface-gray-1" @click="open(row.name)">
          <td class="py-3 pr-4 font-medium text-ink-gray-8">{{ row.name }}</td>
          <td class="py-3 pr-4"><Badge variant="subtle" :theme="statusTheme(row.status)" :label="row.status" /></td>
          <td class="py-3 pr-4 text-ink-gray-7">{{ row.period_start }} – {{ row.period_end }}</td>
          <td class="py-3 pr-4 text-right text-ink-gray-8">{{ money(row.total, row.currency) }}</td>
          <td class="py-3 pr-4 text-right text-ink-gray-8">{{ money(row.amount_paid, row.currency) }}</td>
          <td class="py-3 pr-4 text-right text-ink-gray-8">{{ money(row.total - row.amount_paid, row.currency) }}</td>
          <td class="py-3 text-right"><Button v-if="row.status !== 'Draft'" label="View" @click.stop="open(row.name)" /></td>
        </tr>
        <tr v-if="!(invoices.data || []).length"><td colspan="7" class="py-6 text-ink-gray-5">No invoices yet.</td></tr>
      </tbody>
    </table>
    <InvoiceDialog v-model="showDialog" :name="selected" />
  </div>
</template>
<script setup>
import { ref, watch } from 'vue';
import { Badge, Button, createResource } from 'frappe-ui';
import { store } from '../store';
import InvoiceDialog from '../components/InvoiceDialog.vue';
import { money, statusTheme } from '../utils';
const invoices = createResource({ url: 'billing.api.dashboard.list_invoices', makeParams: () => ({ team: store.team }) });
watch(() => store.team, (t) => t && invoices.reload(), { immediate: true });
const showDialog = ref(false); const selected = ref(null);
function open(name) { selected.value = name; showDialog.value = true; }
</script>
