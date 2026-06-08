<template>
  <div class="flex h-screen overflow-hidden bg-surface-white text-ink-gray-9">
    <aside class="flex w-60 shrink-0 flex-col border-r border-outline-gray-2 bg-surface-gray-1">
      <div class="p-3">
        <div class="flex items-center gap-2 px-1 py-1.5">
          <div class="flex size-7 items-center justify-center rounded bg-surface-gray-5 text-xs font-bold text-ink-white">CB</div>
          <span class="text-sm font-semibold text-ink-gray-9">Cloud Billing</span>
        </div>
        <p class="mt-3 px-1 text-xs font-medium text-ink-gray-5">Team</p>
        <FormControl class="mt-1" type="select" :modelValue="store.team" @update:modelValue="switchTeam" :options="teamOptions" />
        <TabButtons
          v-if="store.isAdmin"
          class="mt-3"
          :buttons="[{ label: 'Customer view', value: 'customer' }, { label: 'Admin view', value: 'admin' }]"
          :modelValue="store.view"
          @update:modelValue="setView"
        />
      </div>
      <nav class="flex flex-1 flex-col gap-0.5 overflow-y-auto px-3">
        <template v-for="it in nav" :key="it.to || it.section">
          <p v-if="it.section" class="mt-3 mb-0.5 px-2.5 text-xs font-medium text-ink-gray-4">{{ it.section }}</p>
          <router-link v-else :to="it.to"
            class="flex items-center gap-2.5 rounded py-1.5 px-2.5 text-sm text-ink-gray-7 transition hover:bg-surface-gray-2"
            exact-active-class="!bg-surface-white !text-ink-gray-9 shadow-sm">
            <component :is="it.icon" class="size-4 text-ink-gray-6" /><span>{{ it.label }}</span>
          </router-link>
        </template>
      </nav>
      <div class="border-t border-outline-gray-2 p-3 text-xs text-ink-gray-5">{{ store.team || '—' }}</div>
    </aside>
    <main class="flex-1 overflow-auto"><div class="mx-auto max-w-5xl px-8 py-8"><router-view /></div></main>
  </div>
</template>
<script setup>
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { FormControl, TabButtons, createResource } from 'frappe-ui';
import LucideLayoutDashboard from '~icons/lucide/layout-dashboard';
import LucideTrendingUp from '~icons/lucide/trending-up';
import LucideReceipt from '~icons/lucide/receipt';
import LucideHistory from '~icons/lucide/history';
import LucideCreditCard from '~icons/lucide/credit-card';
import LucideWallet from '~icons/lucide/wallet';
import LucideUsers from '~icons/lucide/users';
import LucideAward from '~icons/lucide/award';
import LucidePackage from '~icons/lucide/package';
import LucideServer from '~icons/lucide/server';
import LucideLayers from '~icons/lucide/layers';
import LucideCircleAlert from '~icons/lucide/circle-alert';
import LucideGift from '~icons/lucide/gift';
import LucideUserCheck from '~icons/lucide/user-check';
import { store } from './store';
const router = useRouter();
createResource({ url: 'billing.dashboard.whoami', auto: true, onSuccess: (d) => { store.team = d.team; store.isAdmin = d.is_billing_admin; } });
const teams = createResource({ url: 'billing.dashboard.list_switchable_teams', auto: true });
const teamOptions = computed(() => (teams.data || []).map((t) => ({ label: `${t.team} (${t.tier || '—'})`, value: t.team })));
function switchTeam(t) { store.team = t; }
function setView(v) { store.view = v; router.push(v === 'admin' ? '/billing/admin' : '/billing'); }
const customerNav = [
  { label: 'Overview', to: '/billing', icon: LucideLayoutDashboard },
  { label: 'Forecast', to: '/billing/forecast', icon: LucideTrendingUp },
  { label: 'Invoices', to: '/billing/invoices', icon: LucideReceipt },
  { label: 'Payment History', to: '/billing/payments', icon: LucideHistory },
  { label: 'Credits', to: '/billing/credits', icon: LucideWallet },
  { label: 'Payment Methods', to: '/billing/methods', icon: LucideCreditCard },
  { label: 'Trust Tier', to: '/billing/tier', icon: LucideAward },
];
const adminNav = [
  { label: 'Overview', to: '/billing/admin', icon: LucideLayoutDashboard },
  { label: 'Teams', to: '/billing/admin/teams', icon: LucideUsers },
  { label: 'Invoices', to: '/billing/admin/invoices', icon: LucideReceipt },
  { label: 'Catalog', to: '/billing/admin/catalog', icon: LucidePackage },
  { section: 'Analytics' },
  { label: 'Cluster Consumption', to: '/billing/admin/clusters', icon: LucideServer },
  { label: 'Plan Consumption', to: '/billing/admin/plans', icon: LucideLayers },
  { label: 'Payment Failures', to: '/billing/admin/failures', icon: LucideCircleAlert },
  { label: 'Trials & Conversion', to: '/billing/admin/trials', icon: LucideGift },
  { label: 'Retention', to: '/billing/admin/retention', icon: LucideUserCheck },
];
const nav = computed(() => (store.view === 'admin' ? adminNav : customerNav));
</script>
