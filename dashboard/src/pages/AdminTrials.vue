<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-lg font-semibold text-ink-gray-9">Trials & Conversion</h1>
      <p class="mt-0.5 text-sm text-ink-gray-6">Free-tier subsidy is the true compute cost of trial teams — summed from their <span class="font-medium">cost_report</span> invoices (never charged).</p>
    </div>

    <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <div class="rounded-xl border border-outline-gray-2 p-5">
        <p class="text-sm text-ink-gray-6">Still on Trial</p>
        <p class="mt-1 text-2xl font-semibold text-ink-gray-9">{{ d.data?.still_on_trial ?? 0 }}</p>
        <p class="mt-1 text-xs text-ink-gray-5">entry tier “{{ d.data?.entry_tier || '—' }}”</p>
      </div>
      <div class="rounded-xl border border-outline-gray-2 p-5">
        <p class="text-sm text-ink-gray-6">Converted to Paid</p>
        <p class="mt-1 text-2xl font-semibold text-ink-green-3">{{ d.data?.converted ?? 0 }}</p>
        <p class="mt-1 text-xs text-ink-gray-5">{{ ((conv.data?.conversion_rate ?? 0) * 100).toFixed(0) }}% conversion</p>
      </div>
      <div class="rounded-xl border border-outline-gray-2 p-5">
        <p class="text-sm text-ink-gray-6">Active Trial Subsidy</p>
        <p class="mt-1 text-2xl font-semibold text-ink-amber-3">{{ money(d.data?.trial_subsidy_inr) }}</p>
        <p class="mt-1 text-xs text-ink-gray-5">unconverted, INR-equiv.</p>
      </div>
      <div class="rounded-xl border border-outline-gray-2 p-5">
        <p class="text-sm text-ink-gray-6">Total Subsidy Spent</p>
        <p class="mt-1 text-2xl font-semibold text-ink-gray-9">{{ money(d.data?.total_subsidy_inr) }}</p>
        <p class="mt-1 text-xs text-ink-gray-5">incl. {{ money(d.data?.converted_subsidy_inr) }} on later-converted</p>
      </div>
    </div>

    <section>
      <h2 class="mb-2 text-base font-semibold text-ink-gray-9">Subsidy by Team</h2>
      <div class="overflow-hidden rounded-lg border border-outline-gray-2">
        <table class="w-full text-sm">
          <thead><tr class="border-b border-outline-gray-2 bg-surface-gray-1 text-left text-ink-gray-5">
            <th class="px-4 py-2 font-normal">Team</th><th class="px-4 py-2 font-normal">State</th>
            <th class="px-4 py-2 font-normal">Tier</th><th class="px-4 py-2 text-right font-normal">Subsidy</th>
            <th class="px-4 py-2 text-right font-normal">Reports</th><th class="px-4 py-2"></th>
          </tr></thead>
          <tbody>
            <template v-for="t in d.data?.teams || []" :key="t.team">
              <tr class="cursor-pointer border-b border-outline-gray-1 hover:bg-surface-gray-1" @click="toggle(t.team)">
                <td class="px-4 py-2 font-medium text-ink-gray-8">{{ t.team }}</td>
                <td class="px-4 py-2"><Badge variant="subtle" :theme="t.on_trial ? 'orange' : 'green'" :label="t.on_trial ? 'On Trial' : 'Converted'" /></td>
                <td class="px-4 py-2 uppercase text-ink-gray-7">{{ t.tier }}</td>
                <td class="px-4 py-2 text-right text-ink-gray-8">{{ money(t.subsidy, t.currency) }}</td>
                <td class="px-4 py-2 text-right text-ink-gray-6">{{ t.invoices.length }}</td>
                <td class="px-4 py-2 text-right text-ink-gray-4">{{ expanded === t.team ? '▾' : '▸' }}</td>
              </tr>
              <tr v-if="expanded === t.team" :key="t.team + '-d'" class="border-b border-outline-gray-1 bg-surface-gray-1">
                <td colspan="6" class="px-4 py-3">
                  <p class="mb-1.5 text-xs font-medium text-ink-gray-6">Source cost_report invoices</p>
                  <div class="space-y-1">
                    <div v-for="i in t.invoices" :key="i.name" class="flex justify-between text-xs text-ink-gray-7">
                      <span class="font-mono">{{ i.name }}</span>
                      <span class="text-ink-gray-5">{{ i.period_start }} → {{ i.period_end }}</span>
                      <span class="text-ink-gray-8">{{ money(i.subtotal, t.currency) }}</span>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
            <tr v-if="!(d.data?.teams || []).length"><td colspan="6" class="px-4 py-8 text-center text-ink-gray-5">No trial subsidy recorded.</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
<script setup>
import { ref } from 'vue';
import { Badge, createResource } from 'frappe-ui';
import { money } from '../utils';
const d = createResource({ url: 'billing.admin.get_trial_detail', auto: true });
const conv = createResource({ url: 'billing.admin.get_conversion', auto: true });
const expanded = ref(null);
function toggle(team) { expanded.value = expanded.value === team ? null : team; }
</script>
