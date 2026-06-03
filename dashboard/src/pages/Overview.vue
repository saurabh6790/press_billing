<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-ink-gray-9">Billing Overview</h1>
      <Button variant="solid" theme="gray" @click="topup = true">Top Up</Button>
    </div>
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <StatCard label="This month (projected)" :value="money(forecast.data?.projected_total)" :sub="`${forecast.data?.days_remaining ?? '–'} days remaining`" />
      <StatCard label="Credit balance" :value="money(forecast.data?.credit_balance)" />
      <StatCard label="Projected shortfall" :value="money(forecast.data?.shortfall)" :valueClass="forecast.data?.shortfall > 0 ? 'text-ink-amber-3' : 'text-ink-green-3'" />
    </div>
    <section>
      <h2 class="mb-2 text-base font-medium text-ink-gray-8">Active subscriptions</h2>
      <div class="overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white">
        <table class="w-full text-sm">
          <thead class="bg-surface-gray-2 text-left text-ink-gray-5">
            <tr><th class="px-4 py-2 font-medium">Plan</th><th class="px-4 py-2 font-medium">Cluster</th><th class="px-4 py-2 font-medium">Standing</th></tr>
          </thead>
          <tbody>
            <tr v-for="s in subs.data || []" :key="s.name" class="border-t border-outline-gray-1">
              <td class="px-4 py-2 text-ink-gray-8">{{ s.plan }}</td>
              <td class="px-4 py-2 text-ink-gray-7">{{ s.cluster }}</td>
              <td class="px-4 py-2"><Badge variant="subtle" :theme="standingTheme(s.account_standing)" :label="s.account_standing" /></td>
            </tr>
            <tr v-if="!(subs.data || []).length"><td colspan="3" class="px-4 py-4 text-ink-gray-5">No active subscriptions.</td></tr>
          </tbody>
        </table>
      </div>
    </section>
    <TopUpDialog v-model="topup" :team="team" :balance="forecast.data?.credit_balance" :methods="methods.data" @success="forecast.reload()" />
  </div>
</template>
<script setup>
import { ref } from 'vue';
import { Badge, Button, createResource } from 'frappe-ui';
import StatCard from '../components/StatCard.vue';
import TopUpDialog from '../components/TopUpDialog.vue';
import { money, standingTheme } from '../utils';
const topup = ref(false);
const team = ref(null);
createResource({ url: 'press_billing.dashboard.whoami', auto: true, onSuccess: (d) => (team.value = d.team) });
const forecast = createResource({ url: 'press_billing.dashboard.get_forecast', auto: true });
const subs = createResource({ url: 'press_billing.dashboard.list_subscriptions', auto: true });
const methods = createResource({ url: 'press_billing.dashboard.list_payment_methods', auto: true });
</script>
