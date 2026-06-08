<template>
  <div class="space-y-8">
    <!-- trust tier + standing -->
    <div class="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm">
      <span class="text-ink-gray-6">Trust tier: <span class="font-medium text-ink-gray-9">{{ ov.data?.tier || '—' }}</span></span>
      <span class="text-ink-gray-6">Cap: <span class="font-medium text-ink-gray-9">{{ money(ov.data?.max_spend, ov.data?.currency) }}/mo</span></span>
      <span class="text-ink-gray-6">Status: <Badge variant="subtle" :theme="standingTheme(ov.data?.standing)" :label="titleCase(ov.data?.standing)" /></span>
      <span class="text-ink-gray-6">Instances: <span class="font-medium text-ink-gray-9">{{ ov.data?.resources ?? 0 }}</span> across <span class="font-medium text-ink-gray-9">{{ ov.data?.clusters ?? 0 }}</span> region(s)</span>
      <span class="text-ink-gray-6">Billing currency: <span class="font-medium text-ink-gray-9">{{ ov.data?.currency || 'INR' }}</span></span>
    </div>

    <!-- credit shortfall alert (prepaid) -->
    <div v-if="forecast.data?.credit_alert" class="rounded-md border border-outline-red-1 bg-surface-red-1 px-4 py-3 text-sm text-ink-red-4">
      Your projected bill ({{ money(forecast.data.projected_total, fcur) }}) exceeds your wallet balance ({{ money(forecast.data.credit_balance, fcur) }}). Top up {{ money(forecast.data.shortfall, fcur) }} to avoid interruption.
    </div>

    <!-- this-month projection summary → Forecast tab -->
    <div class="flex items-center justify-between rounded-lg border border-outline-gray-2 px-5 py-4">
      <div>
        <p class="text-lg font-semibold text-ink-gray-9">This Month</p>
        <p class="mt-1 text-sm text-ink-gray-6">Projected to {{ forecast.data?.period_end || '—' }} · {{ forecast.data?.days_remaining ?? '—' }} days left</p>
      </div>
      <div class="flex items-center gap-4">
        <p class="text-2xl font-semibold text-ink-gray-9">{{ money(forecast.data?.projected_total, fcur) }}</p>
        <Button label="View forecast" @click="$router.push('/billing/forecast')" />
      </div>
    </div>

    <!-- payment details -->
    <section>
      <h2 class="mb-1 text-base font-semibold text-ink-gray-9">Payment details</h2>
      <div>
        <DetailRow label="Mode of payment">
          <template #desc>{{ mode === 'prepaid' ? 'Drawn from your prepaid wallet' : 'Your card will be charged for monthly usage' }}</template>
          <template #action><FormControl type="select" v-model="mode" :options="[{label:'Card (postpaid)',value:'postpaid'},{label:'Prepaid Credits',value:'prepaid'}]" @change="saveMode" /></template>
        </DetailRow>

        <DetailRow v-if="mode === 'postpaid'" label="Active card">
          <template #desc><span v-if="defaultCard">{{ defaultCard.display_label }}<span v-if="defaultCard.expiry_month"> · exp {{ defaultCard.expiry_month }}/{{ defaultCard.expiry_year }}</span></span><span v-else>No payment method yet</span></template>
          <template #action><Button :label="defaultCard ? 'Manage' : 'Add'" @click="$router.push('/billing/methods')" /></template>
        </DetailRow>

        <DetailRow v-if="mode === 'prepaid'" label="Credit balance">
          <template #desc>{{ money(balance.data?.balance, balance.data?.currency) }}</template>
          <template #action><Button label="+ Add credit" @click="topup = true" /></template>
        </DetailRow>

        <DetailRow label="Billing address">
          <template #desc><span v-if="profile.data?.legal_name">{{ profile.data.legal_name }}<span v-if="profile.data.city">, {{ profile.data.city }}</span><span v-if="profile.data.gstin"> · GSTIN {{ profile.data.gstin }}</span></span><span v-else>Not added yet</span></template>
          <template #action><Button label="Edit" @click="editAddr = true" /></template>
        </DetailRow>
      </div>
    </section>

    <TopUpDialog v-model="topup" :team="store.team" :balance="balance.data?.balance" :hasProfile="!!profile.data?.legal_name" @success="() => { balance.reload(); forecast.reload(); }" />
    <BillingAddressDialog v-model="editAddr" :team="store.team" :profile="profile.data" @success="profile.reload()" />
  </div>
</template>
<script setup>
import { ref, computed, watch } from 'vue';
import { Button, FormControl, Badge, createResource } from 'frappe-ui';
// forecast currency (a team bills in one currency)
import { store } from '../store';
import DetailRow from '../components/DetailRow.vue';
import TopUpDialog from '../components/TopUpDialog.vue';
import BillingAddressDialog from '../components/BillingAddressDialog.vue';
import { money, titleCase, standingTheme } from '../utils';
const mk = (url) => createResource({ url, makeParams: () => ({ team: store.team }) });
const ov = mk('billing.api.dashboard.get_team_overview');
const forecast = mk('billing.api.dashboard.get_forecast');
const balance = mk('billing.api.dashboard.get_credit_balance');
const methods = mk('billing.api.dashboard.list_payment_methods');
const profile = mk('billing.api.dashboard.get_billing_profile');
const settings = mk('billing.api.dashboard.get_billing_settings');
const saveSettings = createResource({ url: 'billing.api.dashboard.save_billing_settings' });
const mode = ref('postpaid');
const fcur = computed(() => forecast.data?.currency || 'INR');
const topup = ref(false); const editAddr = ref(false);
watch(() => store.team, (t) => { if (t) [ov,forecast,balance,methods,profile,settings].forEach((r) => r.reload()); }, { immediate: true });
watch(() => settings.data, (d) => { if (d) mode.value = d.billing_mode || 'postpaid'; });
const defaultCard = computed(() => (methods.data || []).find((m) => m.is_default) || (methods.data || [])[0]);
function saveMode() { saveSettings.submit({ team: store.team, billing_mode: mode.value }).then(() => forecast.reload()); }
</script>
