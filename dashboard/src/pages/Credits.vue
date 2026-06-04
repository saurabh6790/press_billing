<template>
  <div class="space-y-5">
    <div v-if="notice" class="rounded-md px-3 py-2 text-sm" :class="noticeClass">{{ notice.text }}</div>
    <div class="flex items-center justify-between">
      <div><p class="text-sm text-ink-gray-6">Credit balance</p><p class="text-2xl font-semibold text-ink-gray-9">{{ money(balance.data?.balance, cur) }}</p></div>
      <Button variant="solid" theme="gray" label="+ Add credit" @click="topup = true" />
    </div>
    <table class="w-full text-sm">
      <thead><tr class="border-b border-outline-gray-2 text-left text-ink-gray-5">
        <th class="py-2.5 pr-4 font-normal">Date</th><th class="py-2.5 pr-4 font-normal">Description</th>
        <th class="py-2.5 pr-4 text-right font-normal">Amount</th><th class="py-2.5 text-right font-normal">Balance</th>
      </tr></thead>
      <tbody>
        <tr v-for="(e,i) in ledger.data || []" :key="i" class="border-b border-outline-gray-1">
          <td class="py-3 pr-4 text-ink-gray-7">{{ (e.created_at||'').slice(0,10) }}</td>
          <td class="py-3 pr-4 text-ink-gray-8">{{ e.note || (e.reference_name ? `Applied to ${e.reference_name}` : e.entry_type) }}</td>
          <td class="py-3 pr-4 text-right" :class="e.entry_type==='credit' ? 'text-ink-green-3' : 'text-ink-gray-8'">{{ e.entry_type==='credit'?'+':'−' }}{{ money(e.amount, e.currency || cur) }}</td>
          <td class="py-3 text-right text-ink-gray-8">{{ money(e.running_balance, e.currency || cur) }}</td>
        </tr>
        <tr v-if="!(ledger.data || []).length"><td colspan="4" class="py-6 text-ink-gray-5">No credit activity.</td></tr>
      </tbody>
    </table>
    <TopUpDialog v-model="topup" :team="store.team" :balance="balance.data?.balance" :currency="cur" :hasProfile="!!profile.data?.legal_name" @success="() => { balance.reload(); ledger.reload(); }" />
  </div>
</template>
<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Button, createResource } from 'frappe-ui';
import { store } from '../store';
import TopUpDialog from '../components/TopUpDialog.vue';
import { money } from '../utils';
const topup = ref(false);
const route = useRoute(); const router = useRouter();
const notice = ref(null);  // { type: 'success' | 'error' | 'info', text }
const noticeClass = computed(() => ({
  success: 'bg-surface-green-2 text-ink-green-3',
  error: 'bg-surface-red-2 text-ink-red-3',
  info: 'bg-surface-gray-2 text-ink-gray-7',
}[notice.value?.type] || ''));
const mk = (url) => createResource({ url, makeParams: () => ({ team: store.team }) });
const balance = mk('press_billing.dashboard.get_credit_balance');
const cur = computed(() => balance.data?.currency || 'INR');
const ledger = mk('press_billing.dashboard.credit_ledger');
const profile = mk('press_billing.dashboard.get_billing_profile');
const confirmTopup = createResource({ url: 'press_billing.dashboard.confirm_topup' });
watch(() => store.team, (t) => { if (t) [balance,ledger,profile].forEach((r) => r.reload()); }, { immediate: true });

// Return leg of the hosted Stripe Checkout redirect: confirm the session, then
// clean the query so a refresh doesn't re-confirm.
onMounted(async () => {
  const q = route.query;
  if (q.topup === 'success' && q.session) {
    try {
      await confirmTopup.submit({ team: q.team || store.team, gateway: q.gateway, session: q.session });
      balance.reload(); ledger.reload();
      notice.value = { type: 'success', text: 'Wallet topped up.' };
    } catch (e) { notice.value = { type: 'error', text: e.messages?.[0] || e.message || 'Could not confirm payment.' }; }
  } else if (q.topup === 'cancelled') {
    notice.value = { type: 'info', text: 'Top-up cancelled.' };
  }
  if (q.topup) router.replace({ path: route.path, query: {} });
});
</script>
