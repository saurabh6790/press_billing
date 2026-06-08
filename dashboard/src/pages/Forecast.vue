<template>
  <div class="space-y-6">
    <!-- credit shortfall alert (prepaid) -->
    <div v-if="fc.data?.credit_alert" class="rounded-md border border-outline-red-1 bg-surface-red-1 px-4 py-3 text-sm text-ink-red-4">
      Your projected bill ({{ money(fc.data.projected_total, cur) }}) exceeds your wallet balance ({{ money(fc.data.credit_balance, cur) }}). Top up {{ money(fc.data.shortfall, cur) }} to avoid interruption.
    </div>

    <div class="rounded-lg border border-outline-gray-2 px-5 py-4">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-lg font-semibold text-ink-gray-9">This Month</p>
          <p class="mt-1 text-sm text-ink-gray-6">Projected to {{ fc.data?.period_end || '—' }} · {{ fc.data?.days_remaining ?? '—' }} days left · billed in {{ cur }}</p>
        </div>
        <p class="text-2xl font-semibold text-ink-gray-9">{{ money(fc.data?.projected_total, cur) }}</p>
      </div>

      <table v-if="fc.data?.line_items?.length" class="mt-5 w-full text-sm">
        <thead><tr class="border-b border-outline-gray-2 text-left text-ink-gray-5">
          <th class="py-2 pr-4 font-normal">Service</th>
          <th class="py-2 pr-4 text-right font-normal">Usage</th><th class="py-2 text-right font-normal">Amount</th>
        </tr></thead>
        <tbody>
          <tr v-for="(li,i) in fc.data.line_items" :key="i" class="border-b border-outline-gray-1 align-top">
            <td class="py-2 pr-4">
              <div class="flex items-center gap-2"><span class="text-ink-gray-8">{{ li.item }}</span>
                <Badge variant="subtle" :theme="li.kind === 'Overage' ? 'orange' : 'gray'" :label="li.kind" /></div>
              <div class="text-xs text-ink-gray-5">{{ li.detail }}<span v-if="li.subscription_resource"> · {{ li.subscription_resource }}</span></div>
            </td>
            <td class="py-2 pr-4 text-right text-ink-gray-7">{{ li.days ? li.days + ' day(s)' : (li.quantity + (li.unit ? ' ' + li.unit : '')) }}</td>
            <td class="py-2 text-right text-ink-gray-8">{{ money(li.amount, cur) }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="mt-5 text-sm text-ink-gray-5">No running services projected this month.</p>

      <div class="ml-auto mt-4 w-full max-w-xs space-y-1.5 text-sm">
        <div class="flex justify-between"><span class="text-ink-gray-6">Subtotal</span><span class="text-ink-gray-9">{{ money(fc.data?.subtotal, cur) }}</span></div>
        <div v-if="fc.data?.tax_amount" class="flex justify-between"><span class="text-ink-gray-6">{{ fc.data.tax_type }} tax</span><span class="text-ink-gray-9">{{ money(fc.data.tax_amount, cur) }}</span></div>
        <div class="flex justify-between border-t border-outline-gray-2 pt-1.5 font-medium"><span class="text-ink-gray-8">Projected total</span><span class="text-ink-gray-9">{{ money(fc.data?.projected_total, cur) }}</span></div>
        <div v-if="fc.data?.billing_mode === 'prepaid'" class="flex justify-between"><span class="text-ink-gray-6">Wallet balance</span><span class="text-ink-gray-9">{{ money(fc.data?.credit_balance, cur) }}</span></div>
        <div v-if="fc.data?.billing_mode === 'prepaid' && fc.data?.shortfall" class="flex justify-between text-ink-red-4"><span>Shortfall</span><span>{{ money(fc.data.shortfall, cur) }}</span></div>
      </div>
    </div>

    <p class="text-xs text-ink-gray-5">Projected from your running instances' locked prices to month-end — the same engine that produces your invoice.</p>
  </div>
</template>
<script setup>
import { computed, watch } from 'vue';
import { Badge, createResource } from 'frappe-ui';
import { store } from '../store';
import { money } from '../utils';
const fc = createResource({ url: 'billing.api.dashboard.get_forecast', makeParams: () => ({ team: store.team }) });
const cur = computed(() => fc.data?.currency || 'INR');
watch(() => store.team, (t) => t && fc.reload(), { immediate: true });
</script>
