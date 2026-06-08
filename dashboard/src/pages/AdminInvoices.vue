<template>
  <div class="space-y-4">
    <div>
      <h1 class="text-lg font-semibold text-ink-gray-9">Invoices</h1>
      <p class="mt-0.5 text-sm text-ink-gray-6">{{ filtered.length }} invoices · amounts in each team's billing currency</p>
    </div>

    <div class="flex flex-wrap items-end gap-3">
      <div>
        <label class="mb-1 block text-xs text-ink-gray-5">Status</label>
        <FormControl type="select" v-model="fStatus" :options="statusOptions" />
      </div>
      <FormControl class="ml-auto" type="text" v-model="fSearch" placeholder="Search team or invoice…" />
    </div>

    <div class="overflow-hidden rounded-lg border border-outline-gray-2">
      <table class="w-full text-sm">
        <thead><tr class="border-b border-outline-gray-2 bg-surface-gray-1 text-left text-ink-gray-5">
          <th class="px-4 py-2.5 font-normal">Invoice</th>
          <th class="px-4 py-2.5 font-normal">Team</th>
          <th class="px-4 py-2.5 font-normal">Status</th>
          <th class="px-4 py-2.5 font-normal">Period</th>
          <th class="px-4 py-2.5 text-right font-normal">Total</th>
          <th class="px-4 py-2.5 text-right font-normal">Paid</th>
          <th class="px-4 py-2.5 text-right font-normal">Outstanding</th>
        </tr></thead>
        <tbody>
          <tr v-for="r in filtered" :key="r.name" class="border-b border-outline-gray-1 last:border-0 hover:bg-surface-gray-1">
            <td class="px-4 py-3 font-medium text-ink-gray-8">{{ r.name }}</td>
            <td class="px-4 py-3 text-ink-gray-7">{{ r.team }}</td>
            <td class="px-4 py-3"><Badge variant="subtle" :theme="statusTheme(r.status)" :label="r.status" /></td>
            <td class="px-4 py-3 text-ink-gray-7">{{ r.period_start }} – {{ r.period_end }}</td>
            <td class="px-4 py-3 text-right text-ink-gray-8">{{ money(r.total, r.currency) }}</td>
            <td class="px-4 py-3 text-right text-ink-green-3">{{ money(r.amount_paid, r.currency) }}</td>
            <td class="px-4 py-3 text-right" :class="r.outstanding ? 'text-ink-amber-3' : 'text-ink-gray-5'">{{ money(r.outstanding, r.currency) }}</td>
          </tr>
          <tr v-if="!filtered.length"><td colspan="7" class="px-4 py-8 text-center text-ink-gray-5">No invoices match.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
<script setup>
import { ref, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import { Badge, FormControl, createResource } from 'frappe-ui';
import { money, statusTheme } from '../utils';

const route = useRoute();
const invoices = createResource({ url: 'billing.api.admin.list_all_invoices', auto: true });
const fStatus = ref('all');
const fSearch = ref('');

// Collected / Outstanding cards drill in with ?status=paid|outstanding.
watch(() => route.query.status, (s) => { if (s) fStatus.value = String(s); }, { immediate: true });

const statusOptions = [
  { label: 'All', value: 'all' },
  { label: 'Paid', value: 'paid' },
  { label: 'Outstanding (Open + Overdue)', value: 'outstanding' },
  { label: 'Open', value: 'Open' },
  { label: 'Overdue', value: 'Overdue' },
  { label: 'Draft', value: 'Draft' },
];

const filtered = computed(() => (invoices.data || []).filter((r) => {
  if (fStatus.value === 'paid' && r.status !== 'Paid') return false;
  if (fStatus.value === 'outstanding' && !['Open', 'Overdue'].includes(r.status)) return false;
  if (!['all', 'paid', 'outstanding'].includes(fStatus.value) && r.status !== fStatus.value) return false;
  if (fSearch.value) {
    const q = fSearch.value.toLowerCase();
    if (!r.team.toLowerCase().includes(q) && !r.name.toLowerCase().includes(q)) return false;
  }
  return true;
}));
</script>
