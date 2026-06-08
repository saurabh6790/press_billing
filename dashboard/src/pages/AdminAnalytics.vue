<template>
  <div class="space-y-8">
    <!-- trial economics + conversion -->
    <section class="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div class="rounded-lg border border-outline-gray-2 p-5"><p class="text-sm text-ink-gray-6">Trial subsidy (unconverted)</p><p class="mt-1 text-xl font-semibold text-ink-amber-3">{{ money(trial.data?.unconverted_subsidy) }}</p></div>
      <div class="rounded-lg border border-outline-gray-2 p-5"><p class="text-sm text-ink-gray-6">Trial cost (later converted)</p><p class="mt-1 text-xl font-semibold text-ink-green-3">{{ money(trial.data?.converted_cost) }}</p></div>
      <div class="rounded-lg border border-outline-gray-2 p-5"><p class="text-sm text-ink-gray-6">Conversion rate</p><p class="mt-1 text-xl font-semibold text-ink-gray-9">{{ ((conv.data?.conversion_rate ?? 0) * 100).toFixed(0) }}%</p><p class="mt-1 text-xs text-ink-gray-5">{{ conv.data?.paid ?? 0 }} paid / {{ conv.data?.trial ?? 0 }} trial</p></div>
    </section>

    <Panel title="Cluster-wise consumption" :rows="cluster.data" :cols="['Cluster','Resources','Monthly run-rate']" :fields="['cluster','resources','monthly']" money-field="monthly" />
    <Panel title="Plan-wise consumption" :rows="plan.data" :cols="['Plan','Resources','Monthly run-rate']" :fields="['plan','resources','monthly']" money-field="monthly" />

    <section>
      <h2 class="mb-2 text-base font-semibold text-ink-gray-9">Delinquent Teams</h2>
      <div class="overflow-hidden rounded-lg border border-outline-gray-2">
        <table class="w-full text-sm">
          <thead><tr class="border-b border-outline-gray-2 bg-surface-gray-1 text-left text-ink-gray-5"><th class="px-4 py-2 font-normal">Team</th><th class="px-4 py-2 font-normal">Status</th><th class="px-4 py-2 text-right font-normal">Outstanding</th><th class="px-4 py-2 font-normal">Overdue Invoices</th></tr></thead>
          <tbody>
            <tr v-for="d in delinquent.data || []" :key="d.team" class="border-b border-outline-gray-1 last:border-0">
              <td class="px-4 py-2 font-medium text-ink-gray-8">{{ d.team }}</td>
              <td class="px-4 py-2"><Badge variant="subtle" :theme="standingTheme(d.standing)" :label="titleCase(d.standing)" /></td>
              <td class="px-4 py-2 text-right text-ink-gray-8">{{ money(d.outstanding) }}</td>
              <td class="px-4 py-2 text-ink-gray-6">{{ (d.invoices || []).map(i => i.name).join(', ') || '—' }}</td>
            </tr>
            <tr v-if="!(delinquent.data || []).length"><td colspan="4" class="px-4 py-6 text-center text-ink-gray-5">None.</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <section>
      <h2 class="mb-2 text-base font-semibold text-ink-gray-9">Payment Failures</h2>
      <div class="overflow-hidden rounded-lg border border-outline-gray-2">
        <table class="w-full text-sm">
          <thead><tr class="border-b border-outline-gray-2 bg-surface-gray-1 text-left text-ink-gray-5"><th class="px-4 py-2 font-normal">Team</th><th class="px-4 py-2 font-normal">Invoice</th><th class="px-4 py-2 text-right font-normal">Amount</th><th class="px-4 py-2 font-normal">Reason</th><th class="px-4 py-2 font-normal">When</th></tr></thead>
          <tbody>
            <tr v-for="f in failures.data || []" :key="f.name" class="border-b border-outline-gray-1 last:border-0">
              <td class="px-4 py-2 font-medium text-ink-gray-8">{{ f.team }}</td>
              <td class="px-4 py-2 text-ink-gray-7">{{ f.invoice }}</td>
              <td class="px-4 py-2 text-right text-ink-gray-8">{{ money(f.amount) }}</td>
              <td class="px-4 py-2 text-ink-red-4">{{ f.failure_reason || f.failure_code || '—' }}</td>
              <td class="px-4 py-2 text-ink-gray-6">{{ (f.creation||'').slice(0,10) }}</td>
            </tr>
            <tr v-if="!(failures.data || []).length"><td colspan="5" class="px-4 py-6 text-center text-ink-gray-5">None.</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
<script setup>
import { Badge, createResource } from 'frappe-ui';
import Panel from '../components/Panel.vue';
import { money, titleCase, standingTheme } from '../utils';
const a = (url) => createResource({ url, auto: true });
const trial = a('billing.api.admin.get_trial_costs_detail');
const conv = a('billing.api.admin.get_conversion');
const cluster = a('billing.api.admin.get_cluster_consumption');
const plan = a('billing.api.admin.get_plan_consumption');
const delinquent = a('billing.api.admin.get_delinquent_teams');
const failures = a('billing.api.admin.get_payment_failures');
</script>
