<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-ink-gray-9">Credits</h1>
      <Button variant="solid" theme="gray" @click="topup = true">Top Up</Button>
    </div>
    <StatCard label="Wallet balance" :value="money(balance.data?.balance)" />
    <div class="overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white">
      <table class="w-full text-sm">
        <thead class="bg-surface-gray-2 text-left text-ink-gray-5">
          <tr><th class="px-4 py-2 font-medium">Type</th><th class="px-4 py-2 font-medium">Amount</th><th class="px-4 py-2 font-medium">Balance</th><th class="px-4 py-2 font-medium">Note</th></tr>
        </thead>
        <tbody>
          <tr v-for="(e, i) in ledger.data || []" :key="i" class="border-t border-outline-gray-1">
            <td class="px-4 py-2"><Badge variant="subtle" :theme="e.entry_type === 'credit' ? 'green' : 'orange'" :label="e.entry_type" /></td>
            <td class="px-4 py-2 text-ink-gray-8">{{ money(e.amount) }}</td>
            <td class="px-4 py-2 text-ink-gray-8">{{ money(e.running_balance) }}</td>
            <td class="px-4 py-2 text-ink-gray-5">{{ e.note }}</td>
          </tr>
          <tr v-if="!(ledger.data || []).length"><td colspan="4" class="px-4 py-4 text-ink-gray-5">No credit activity.</td></tr>
        </tbody>
      </table>
    </div>
    <TopUpDialog v-model="topup" :team="team" :balance="balance.data?.balance" :methods="methods.data" @success="() => { balance.reload(); ledger.reload(); }" />
  </div>
</template>
<script setup>
import { ref } from 'vue';
import { Badge, Button, createResource } from 'frappe-ui';
import StatCard from '../components/StatCard.vue';
import TopUpDialog from '../components/TopUpDialog.vue';
import { money } from '../utils';
const topup = ref(false); const team = ref(null);
createResource({ url: 'press_billing.dashboard.whoami', auto: true, onSuccess: (d) => (team.value = d.team) });
const balance = createResource({ url: 'press_billing.dashboard.get_credit_balance', auto: true });
const ledger = createResource({ url: 'press_billing.dashboard.credit_ledger', auto: true });
const methods = createResource({ url: 'press_billing.dashboard.list_payment_methods', auto: true });
</script>
