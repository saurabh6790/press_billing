<template>
  <Dialog v-model="show" :options="{ title: data?.team || 'Team', size: '4xl' }">
    <template #body-content>
      <div v-if="d.data" class="space-y-6">
        <div class="flex gap-8 text-sm">
          <span class="text-ink-gray-6">Credit balance: <span class="font-medium text-ink-gray-9">{{ money(d.data.credit_balance) }}</span></span>
        </div>
        <section v-for="sec in sections" :key="sec.title">
          <h3 class="mb-1.5 text-sm font-semibold text-ink-gray-8">{{ sec.title }}</h3>
          <table class="w-full text-sm">
            <thead><tr class="border-b border-outline-gray-2 text-left text-ink-gray-5">
              <th v-for="c in sec.cols" :key="c" class="py-1.5 pr-4 font-normal">{{ c }}</th>
            </tr></thead>
            <tbody>
              <tr v-for="(r, i) in d.data[sec.key]" :key="i" class="border-b border-outline-gray-1">
                <td v-for="f in sec.fields" :key="f" class="py-2 pr-4 text-ink-gray-8">
                  <Badge v-if="f === 'account_standing'" variant="subtle" :theme="standingTheme(r[f])" :label="titleCase(r[f])" />
                  <Badge v-else-if="f === 'status' && sec.key === 'payment_attempts'" variant="subtle" :theme="attemptTheme(r[f])" :label="attemptLabel(r[f])" />
                  <Badge v-else-if="f === 'status'" variant="subtle" :theme="statusTheme(r[f])" :label="r[f]" />
                  <span v-else-if="f === 'total' || f === 'amount'">{{ money(r[f]) }}</span>
                  <span v-else>{{ r[f] || '—' }}</span>
                </td>
              </tr>
              <tr v-if="!d.data[sec.key]?.length"><td :colspan="sec.cols.length" class="py-2 text-ink-gray-5">None.</td></tr>
            </tbody>
          </table>
        </section>
      </div>
      <div v-else class="py-8 text-center"><Spinner class="h-6" /></div>
    </template>
  </Dialog>
</template>
<script setup>
import { computed, watch } from 'vue';
import { Dialog, Badge, Spinner, createResource } from 'frappe-ui';
import { money, standingTheme, statusTheme, titleCase, attemptTheme, attemptLabel } from '../utils';
const props = defineProps({ modelValue: Boolean, data: Object });
const emit = defineEmits(['update:modelValue']);
const show = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) });
const d = createResource({ url: 'billing.api.admin.get_team_billing' });
watch(() => props.data, (t) => { if (t?.team) d.submit({ team: t.team }); });
const sections = [
  { title: 'Subscriptions', key: 'subscriptions', cols: ['Plan', 'Cluster', 'Status'], fields: ['plan', 'cluster', 'account_standing'] },
  { title: 'Invoices', key: 'invoices', cols: ['Invoice', 'Status', 'Total', 'Period End'], fields: ['name', 'status', 'total', 'period_end'] },
  { title: 'Payment Attempts', key: 'payment_attempts', cols: ['Attempt', 'Status', 'Amount', 'Resolved By'], fields: ['name', 'status', 'amount', 'resolved_by'] },
];
</script>
