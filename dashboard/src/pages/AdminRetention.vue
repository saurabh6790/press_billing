<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-lg font-semibold text-ink-gray-9">Customer Retention</h1>
      <p class="mt-0.5 text-sm text-ink-gray-6">Account health across the base — retained (active), at-risk (past due) and churned (suspended).</p>
    </div>

    <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <div class="rounded-xl border border-outline-gray-2 p-5">
        <p class="text-sm text-ink-gray-6">Retention Rate</p>
        <p class="mt-1 text-2xl font-semibold text-ink-gray-9">{{ ((r.data?.retention_rate ?? 0) * 100).toFixed(0) }}%</p>
        <p class="mt-1 text-xs text-ink-gray-5">non-churned of {{ r.data?.total_teams ?? 0 }} teams</p>
      </div>
      <div class="rounded-xl border border-outline-gray-2 p-5">
        <p class="text-sm text-ink-gray-6">Active</p>
        <p class="mt-1 text-2xl font-semibold text-ink-green-3">{{ r.data?.active ?? 0 }}</p>
        <p class="mt-1 text-xs text-ink-gray-5">{{ ((r.data?.active_rate ?? 0) * 100).toFixed(0) }}% paying on time</p>
      </div>
      <div class="rounded-xl border border-outline-gray-2 p-5">
        <p class="text-sm text-ink-gray-6">At Risk</p>
        <p class="mt-1 text-2xl font-semibold text-ink-amber-3">{{ r.data?.at_risk ?? 0 }}</p>
        <p class="mt-1 text-xs text-ink-gray-5">past due — in dunning</p>
      </div>
      <div class="rounded-xl border border-outline-gray-2 p-5">
        <p class="text-sm text-ink-gray-6">Churned</p>
        <p class="mt-1 text-2xl font-semibold text-ink-red-3">{{ r.data?.churned ?? 0 }}</p>
        <p class="mt-1 text-xs text-ink-gray-5">suspended</p>
      </div>
    </div>

    <!-- health bar -->
    <div class="rounded-xl border border-outline-gray-2 p-5">
      <p class="mb-2 text-sm text-ink-gray-6">Base composition</p>
      <div class="flex h-3 w-full overflow-hidden rounded-full">
        <div class="bg-ink-green-3" :style="{ width: pct('active') }" :title="`Active: ${r.data?.active}`"></div>
        <div class="bg-ink-amber-3" :style="{ width: pct('at_risk') }" :title="`At risk: ${r.data?.at_risk}`"></div>
        <div class="bg-ink-red-3" :style="{ width: pct('churned') }" :title="`Churned: ${r.data?.churned}`"></div>
      </div>
      <div class="mt-2 flex gap-4 text-xs text-ink-gray-5">
        <span class="flex items-center gap-1.5"><span class="size-2.5 rounded-full bg-ink-green-3"></span>Active</span>
        <span class="flex items-center gap-1.5"><span class="size-2.5 rounded-full bg-ink-amber-3"></span>At risk</span>
        <span class="flex items-center gap-1.5"><span class="size-2.5 rounded-full bg-ink-red-3"></span>Churned</span>
      </div>
    </div>

    <section>
      <h2 class="mb-2 text-base font-semibold text-ink-gray-9">Teams</h2>
      <div class="overflow-hidden rounded-lg border border-outline-gray-2">
        <table class="w-full text-sm">
          <thead><tr class="border-b border-outline-gray-2 bg-surface-gray-1 text-left text-ink-gray-5">
            <th class="px-4 py-2 font-normal">Team</th><th class="px-4 py-2 font-normal">Status</th>
          </tr></thead>
          <tbody>
            <tr v-for="t in r.data?.teams || []" :key="t.team" class="border-b border-outline-gray-1 last:border-0">
              <td class="px-4 py-2 font-medium text-ink-gray-8">{{ t.team }}</td>
              <td class="px-4 py-2"><Badge variant="subtle" :theme="standingTheme(t.standing)" :label="titleCase(t.standing)" /></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
<script setup>
import { createResource } from 'frappe-ui';
import { Badge } from 'frappe-ui';
import { titleCase, standingTheme } from '../utils';
const r = createResource({ url: 'billing.api.admin.get_retention', auto: true });
function pct(k) {
  const t = r.data?.total_teams || 0;
  return t ? `${((r.data[k] || 0) / t) * 100}%` : '0%';
}
</script>
