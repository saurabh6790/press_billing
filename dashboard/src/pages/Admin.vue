<template>
  <div class="space-y-6">
    <h1 class="text-xl font-semibold text-ink-gray-9">Admin · Billing</h1>
    <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <StatCard label="MRR" :value="money(m.data?.mrr)" />
      <StatCard label="Teams" :value="m.data?.team_count ?? 0" :sub="`${m.data?.paying_on_time ?? 0} on time`" />
      <StatCard label="Delinquent" :value="m.data?.delinquent ?? 0" :sub="`${m.data?.suspended ?? 0} suspended`" valueClass="text-ink-amber-3" />
      <StatCard label="Payment failures" :value="m.data?.payment_failures ?? 0" valueClass="text-ink-red-3" />
    </div>
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <StatCard label="Total billed" :value="money(s.data?.total_billed)" />
      <StatCard label="Outstanding" :value="money(s.data?.outstanding)" valueClass="text-ink-amber-3" />
    </div>
    <section>
      <h2 class="mb-2 text-base font-medium text-ink-gray-8">Teams</h2>
      <div class="overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white">
        <table class="w-full text-sm">
          <thead class="bg-surface-gray-2 text-left text-ink-gray-5">
            <tr><th class="px-4 py-2 font-medium">Team</th><th class="px-4 py-2 font-medium">Standing</th><th class="px-4 py-2 font-medium">MRR</th><th class="px-4 py-2 font-medium">Open invoices</th><th class="px-4 py-2 font-medium">Credit</th></tr>
          </thead>
          <tbody>
            <tr v-for="t in teams.data || []" :key="t.team" class="border-t border-outline-gray-1">
              <td class="px-4 py-2 font-medium text-ink-gray-8">{{ t.team }}</td>
              <td class="px-4 py-2"><Badge variant="subtle" :theme="standingTheme(t.standing)" :label="t.standing" /></td>
              <td class="px-4 py-2 text-ink-gray-8">{{ money(t.mrr) }}</td>
              <td class="px-4 py-2 text-ink-gray-7">{{ t.open_invoices }}</td>
              <td class="px-4 py-2 text-ink-gray-7">{{ money(t.credit_balance) }}</td>
            </tr>
            <tr v-if="!(teams.data || []).length"><td colspan="5" class="px-4 py-4 text-ink-gray-5">No teams.</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
<script setup>
import { Badge, createResource } from 'frappe-ui';
import StatCard from '../components/StatCard.vue';
import { money, standingTheme } from '../utils';
const m = createResource({ url: 'press_billing.admin.get_metrics', auto: true });
const s = createResource({ url: 'press_billing.admin.get_summary', auto: true });
const teams = createResource({ url: 'press_billing.admin.list_teams', auto: true });
</script>
