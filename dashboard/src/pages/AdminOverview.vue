<template>
  <div class="space-y-6">
    <div class="flex items-end justify-between">
      <div>
        <h1 class="text-lg font-semibold text-ink-gray-9">Overview</h1>
        <p class="mt-0.5 text-sm text-ink-gray-6">Revenue, collection and account health across all teams. All figures INR-equivalent.</p>
      </div>
    </div>

    <!-- headline stat cards — each drills into a filtered list -->
    <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <router-link v-for="s in stats" :key="s.label" :to="s.to"
        class="group block rounded-xl border border-outline-gray-2 bg-surface-white p-5 transition hover:border-outline-gray-3 hover:shadow-sm">
        <div class="flex items-center justify-between">
          <p class="text-sm text-ink-gray-6">{{ s.label }}</p>
          <component :is="s.icon" class="size-4 text-ink-gray-4" />
        </div>
        <p class="mt-2 text-2xl font-semibold" :class="s.cls || 'text-ink-gray-9'">{{ s.value }}</p>
        <p class="mt-1 flex items-center gap-1 text-xs text-ink-gray-5">
          <span>{{ s.sub }}</span>
          <span class="ml-auto text-ink-gray-4 opacity-0 transition group-hover:opacity-100">View →</span>
        </p>
      </router-link>
    </div>

    <!-- billed/collected/outstanding strip — also drillable -->
    <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <router-link to="/billing/admin/invoices" class="block rounded-xl border border-outline-gray-2 p-5 transition hover:shadow-sm">
        <p class="text-sm text-ink-gray-6">Total Billed</p><p class="mt-1 text-xl font-semibold text-ink-gray-9">{{ money(sum.data?.total_billed) }}</p></router-link>
      <router-link to="/billing/admin/invoices?status=paid" class="block rounded-xl border border-outline-gray-2 p-5 transition hover:shadow-sm">
        <p class="text-sm text-ink-gray-6">Collected</p><p class="mt-1 text-xl font-semibold text-ink-green-3">{{ money(sum.data?.total_collected) }}</p></router-link>
      <router-link to="/billing/admin/invoices?status=outstanding" class="block rounded-xl border border-outline-gray-2 p-5 transition hover:shadow-sm">
        <p class="text-sm text-ink-gray-6">Outstanding</p><p class="mt-1 text-xl font-semibold text-ink-amber-3">{{ money(sum.data?.outstanding) }}</p></router-link>
      <div class="rounded-xl border border-outline-gray-2 p-5">
        <p class="text-sm text-ink-gray-6">Collection Rate</p>
        <p class="mt-1 text-xl font-semibold text-ink-gray-9">{{ collectionRate }}%</p>
        <div class="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-gray-3">
          <div class="h-full rounded-full bg-ink-green-3" :style="{ width: collectionRate + '%' }"></div>
        </div>
      </div>
    </div>

    <!-- at-a-glance charts -->
    <RevenueChart title="Monthly Recurring Revenue" :data="trend.data || []" />
    <BarChart title="Payments Collected" subtitle="Per month, INR-equivalent" :data="trend.data || []" field="collected" />
  </div>
</template>
<script setup>
import { computed } from 'vue';
import { createResource } from 'frappe-ui';
import RevenueChart from '../components/RevenueChart.vue';
import BarChart from '../components/BarChart.vue';
import { money } from '../utils';
import LucideTrendingUp from '~icons/lucide/trending-up';
import LucideUsers from '~icons/lucide/users';
import LucideTriangleAlert from '~icons/lucide/triangle-alert';
import LucideCreditCard from '~icons/lucide/credit-card';

const m = createResource({ url: 'billing.admin.get_metrics', auto: true });
const sum = createResource({ url: 'billing.admin.get_summary', auto: true });
const trend = createResource({ url: 'billing.admin.get_revenue_trend', auto: true });

const stats = computed(() => [
  { label: 'MRR', value: money(m.data?.mrr), sub: `${m.data?.active_subscriptions ?? 0} active subscriptions`, icon: LucideTrendingUp, to: '/billing/admin/teams' },
  { label: 'Teams', value: m.data?.team_count ?? 0, sub: `${m.data?.paying_on_time ?? 0} paying on time`, icon: LucideUsers, to: '/billing/admin/teams' },
  { label: 'Delinquent', value: m.data?.delinquent ?? 0, sub: `${m.data?.suspended ?? 0} suspended`, cls: 'text-ink-amber-3', icon: LucideTriangleAlert, to: '/billing/admin/teams?status=delinquent' },
  { label: 'Payment Failures', value: m.data?.payment_failures ?? 0, sub: 'View failed charges', cls: 'text-ink-red-3', icon: LucideCreditCard, to: '/billing/admin/failures' },
]);

const collectionRate = computed(() => {
  const b = sum.data?.total_billed || 0, c = sum.data?.total_collected || 0;
  return b ? Math.min(100, Math.round((c / b) * 100)) : 0;
});
</script>
