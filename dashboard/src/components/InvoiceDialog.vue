<template>
  <Dialog v-model="show" :options="{ title: inv.data?.name || 'Invoice', size: '3xl' }">
    <template #body-content>
      <div v-if="inv.data" class="space-y-5">
        <div class="flex flex-wrap gap-x-8 gap-y-1 text-sm">
          <span class="text-ink-gray-6">Period: <span class="text-ink-gray-9">{{ inv.data.period_start }} → {{ inv.data.period_end }}</span></span>
          <span class="text-ink-gray-6">Status: <Badge variant="subtle" :theme="statusTheme(inv.data.status)" :label="inv.data.status" /></span>
          <span class="text-ink-gray-6">Type: <span class="text-ink-gray-9">{{ invoiceTypeLabel(inv.data.invoice_type) }}</span></span>
        </div>

        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-outline-gray-2 text-left text-ink-gray-5">
              <th class="py-2 pr-4 font-normal">Item</th>
              <th class="py-2 pr-4 text-right font-normal">Qty</th>
              <th class="py-2 pr-4 text-right font-normal">Rate</th>
              <th class="py-2 text-right font-normal">Amount</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(li, i) in inv.data.items" :key="i" class="border-b border-outline-gray-1 align-top">
              <td class="py-2 pr-4">
                <div class="flex items-center gap-2">
                  <span class="text-ink-gray-8">{{ li.item }}</span>
                  <Badge variant="subtle" :theme="li.kind === 'Overage' ? 'orange' : 'gray'" :label="li.kind" />
                </div>
                <div class="text-xs text-ink-gray-5">{{ li.detail }}<span v-if="li.subscription_resource"> · {{ li.subscription_resource }}</span></div>
              </td>
              <td class="py-2 pr-4 text-right text-ink-gray-7">{{ li.days ? li.days + ' day(s)' : (li.quantity + (li.unit ? ' ' + li.unit : '')) }}</td>
              <td class="py-2 pr-4 text-right text-ink-gray-7">{{ money(li.rate, inv.data.currency) }}<span v-if="li.kind === 'Overage'" class="text-ink-gray-5">/{{ li.unit }}</span></td>
              <td class="py-2 text-right text-ink-gray-8">{{ money(li.amount, inv.data.currency) }}</td>
            </tr>
            <tr v-if="!inv.data.items?.length"><td colspan="4" class="py-4 text-ink-gray-5">No line items.</td></tr>
          </tbody>
        </table>

        <div class="ml-auto w-full max-w-xs space-y-1.5 text-sm">
          <div class="flex justify-between"><span class="text-ink-gray-6">Subtotal</span><span class="text-ink-gray-9">{{ money(inv.data.subtotal, inv.data.currency) }}</span></div>
          <div v-if="inv.data.output_tax_amount" class="flex justify-between"><span class="text-ink-gray-6">{{ inv.data.output_tax_type }} tax</span><span class="text-ink-gray-9">{{ money(inv.data.output_tax_amount, inv.data.currency) }}</span></div>
          <div v-if="inv.data.zero_rating_reason" class="flex justify-between"><span class="text-ink-gray-6">Tax (zero-rated)</span><span class="text-ink-gray-9">{{ inv.data.zero_rating_reason }}</span></div>
          <div v-if="inv.data.credit_applied" class="flex justify-between"><span class="text-ink-gray-6">Credits applied</span><span class="text-ink-green-3">−{{ money(inv.data.credit_applied, inv.data.currency) }}</span></div>
          <div class="flex justify-between border-t border-outline-gray-2 pt-1.5 font-medium"><span class="text-ink-gray-8">Total</span><span class="text-ink-gray-9">{{ money(inv.data.total, inv.data.currency) }}</span></div>
          <div class="flex justify-between"><span class="text-ink-gray-6">Amount paid</span><span class="text-ink-gray-9">{{ money(inv.data.amount_paid, inv.data.currency) }}</span></div>
          <div class="flex justify-between"><span class="text-ink-gray-6">Amount due</span><span class="text-ink-gray-9">{{ money((inv.data.expected_collection || inv.data.total) - inv.data.amount_paid, inv.data.currency) }}</span></div>
        </div>
      </div>
      <div v-else class="py-8 text-center"><Spinner class="h-6" /></div>
    </template>
  </Dialog>
</template>
<script setup>
import { computed, watch } from 'vue';
import { Dialog, Badge, Spinner, createResource } from 'frappe-ui';
import { money, statusTheme, invoiceTypeLabel } from '../utils';
const props = defineProps({ modelValue: Boolean, name: String });
const emit = defineEmits(['update:modelValue']);
const show = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) });
const inv = createResource({ url: 'billing.dashboard.get_invoice' });
watch(() => props.name, (n) => { if (n) inv.submit({ name: n }); });
</script>
