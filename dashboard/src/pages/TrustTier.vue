<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-lg font-semibold text-ink-gray-9">Trust Tier</h1>
        <p class="mt-0.5 text-sm text-ink-gray-6">Your tier sets your spend headroom and how many instances you can run. Pay reliably to unlock more.</p>
      </div>
      <Badge v-if="t.data?.current" size="lg" theme="blue" :label="`Tier ${(t.data.current.tier || '').toUpperCase()}`" />
    </div>

    <!-- current limits -->
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div class="rounded-xl border border-outline-gray-2 p-5">
        <p class="text-sm text-ink-gray-6">Monthly Spend Cap</p>
        <p class="mt-1 text-2xl font-semibold text-ink-gray-9">{{ money(t.data?.current?.max_spend, cur) }}</p>
        <p class="mt-1 text-xs text-ink-gray-5">The most you can accrue per month at this tier.</p>
      </div>
      <div class="rounded-xl border border-outline-gray-2 p-5">
        <p class="text-sm text-ink-gray-6">Instance Limit</p>
        <p class="mt-1 text-2xl font-semibold text-ink-gray-9">{{ t.data?.progress?.resources_used ?? 0 }} / {{ t.data?.current?.max_resource_count ?? '—' }}</p>
        <p class="mt-1 text-xs text-ink-gray-5">Running instances allowed at this tier.</p>
      </div>
    </div>

    <!-- progress to next tier -->
    <div v-if="t.data?.next" class="rounded-xl border border-outline-gray-2 p-5">
      <div class="flex items-center justify-between">
        <p class="text-base font-semibold text-ink-gray-9">Progress to Tier {{ (t.data.next.tier || '').toUpperCase() }}</p>
        <span class="text-xs text-ink-gray-5">unlocks {{ money(t.data.next.max_spend, cur) }}/mo · {{ t.data.next.max_resource_count }} instances</span>
      </div>
      <div class="mt-4 space-y-4">
        <div>
          <div class="mb-1 flex justify-between text-sm"><span class="text-ink-gray-7">Paid invoices</span>
            <span class="text-ink-gray-6">{{ t.data.progress.paid_invoices }} / {{ t.data.next.min_paid_invoices }}</span></div>
          <Bar :value="t.data.progress.paid_invoices" :max="t.data.next.min_paid_invoices" />
        </div>
        <div>
          <div class="mb-1 flex justify-between text-sm"><span class="text-ink-gray-7">Cumulative paid</span>
            <span class="text-ink-gray-6">{{ money(t.data.progress.cumulative_paid, cur) }} / {{ money(t.data.next.min_cumulative_paid, cur) }}</span></div>
          <Bar :value="t.data.progress.cumulative_paid" :max="t.data.next.min_cumulative_paid" />
        </div>
      </div>
    </div>
    <div v-else-if="t.data?.is_top_tier" class="rounded-xl border border-outline-green-2 bg-surface-green-1 px-5 py-4 text-sm text-ink-green-4">
      🏆 You're on the highest trust tier — maximum spend headroom and instance limits.
    </div>

    <!-- full ladder -->
    <section>
      <h2 class="mb-2 text-base font-semibold text-ink-gray-9">All Tiers</h2>
      <div class="overflow-hidden rounded-lg border border-outline-gray-2">
        <table class="w-full text-sm">
          <thead><tr class="border-b border-outline-gray-2 bg-surface-gray-1 text-left text-ink-gray-5">
            <th class="px-4 py-2 font-normal">Tier</th><th class="px-4 py-2 text-right font-normal">Spend Cap</th>
            <th class="px-4 py-2 text-right font-normal">Instances</th><th class="px-4 py-2 text-right font-normal">Min Paid Invoices</th>
            <th class="px-4 py-2 text-right font-normal">Min Cumulative Paid</th>
          </tr></thead>
          <tbody>
            <tr v-for="l in t.data?.all_levels || []" :key="l.tier"
              class="border-b border-outline-gray-1 last:border-0"
              :class="l.tier === t.data?.current?.tier ? 'bg-surface-blue-1' : ''">
              <td class="px-4 py-2 font-medium text-ink-gray-8">
                {{ (l.tier || '').toUpperCase() }}
                <Badge v-if="l.tier === t.data?.current?.tier" variant="subtle" theme="blue" label="You" class="ml-1" />
              </td>
              <td class="px-4 py-2 text-right text-ink-gray-7">{{ money(l.max_spend, cur) }}</td>
              <td class="px-4 py-2 text-right text-ink-gray-7">{{ l.max_resource_count }}</td>
              <td class="px-4 py-2 text-right text-ink-gray-7">{{ l.min_paid_invoices }}</td>
              <td class="px-4 py-2 text-right text-ink-gray-7">{{ money(l.min_cumulative_paid, cur) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
<script setup>
import { computed, watch, h } from 'vue';
import { Badge, createResource } from 'frappe-ui';
import { store } from '../store';
import { money } from '../utils';

const t = createResource({ url: 'billing.dashboard.get_trust_tier', makeParams: () => ({ team: store.team }) });
watch(() => store.team, (v) => v && t.reload(), { immediate: true });
const cur = computed(() => t.data?.currency || 'INR');

// tiny inline progress bar
const Bar = (props) => {
  const pct = props.max ? Math.min(100, (props.value / props.max) * 100) : 0;
  return h('div', { class: 'h-2 w-full overflow-hidden rounded-full bg-surface-gray-3' },
    [h('div', { class: 'h-full rounded-full bg-ink-blue-3', style: { width: pct + '%' } })]);
};
</script>
