<template>
  <Dialog v-model="show" :options="{ title: 'Add credit', size: 'xl' }">
    <template #body-content>
      <div class="space-y-4">
        <p class="text-sm text-ink-gray-6">Current balance: <span class="font-medium text-ink-gray-9">{{ money(balance, currency) }}</span></p>
        <div class="flex flex-wrap gap-2">
          <Button v-for="q in quick" :key="q" :variant="amount == q ? 'solid' : 'subtle'" theme="gray" @click="amount = q">{{ money(q, currency) }}</Button>
        </div>
        <FormControl type="number" :label="`Amount (${curSymbol(currency)})`" v-model="amount" />
        <div v-if="!hasProfile">
          <p class="mb-2 text-sm font-medium text-ink-gray-8">Billing details</p>
          <BillingFields :fields="form" />
        </div>
        <p class="rounded-md bg-surface-gray-2 px-3 py-2 text-xs text-ink-gray-6">
          Opens a secure checkout. Your wallet is credited only after the payment is confirmed server-side.
        </p>
        <ErrorMessage :message="error" />
      </div>
    </template>
    <template #actions>
      <Button variant="solid" theme="gray" :loading="loading" @click="submit">Pay {{ money(amount, currency) }}</Button>
    </template>
  </Dialog>
</template>
<script setup>
import { reactive, ref, computed } from 'vue';
import { Dialog, Button, FormControl, ErrorMessage, createResource } from 'frappe-ui';
import BillingFields from './BillingFields.vue';
import { openRazorpay, money, curSymbol } from '../utils';
const props = defineProps({ modelValue: Boolean, team: String, balance: Number, hasProfile: Boolean, currency: { type: String, default: 'INR' } });
const emit = defineEmits(['update:modelValue', 'success']);
const show = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) });
const quick = [1000, 2000, 5000, 10000];
const amount = ref(5000);
const form = reactive({ legal_name: '', gstin: '', email: '', phone: '', address_line1: '', city: '', state: '', pincode: '' });
const error = ref(''); const loading = ref(false);
const saveProfile = createResource({ url: 'billing.dashboard.save_billing_profile' });
const createOrder = createResource({ url: 'billing.dashboard.create_topup_order' });
const confirm = createResource({ url: 'billing.dashboard.confirm_topup' });
async function submit() {
  error.value = ''; loading.value = true;
  try {
    if (!props.hasProfile) await saveProfile.submit({ team: props.team, ...form });
    const order = await createOrder.submit({ team: props.team, amount: amount.value });
    if (order.adapter_key === 'razorpay') {
      const resp = await openRazorpay({ key: order.key_id, order_id: order.order_id, amount: order.amount,
        currency: order.currency, description: 'Wallet top-up', prefill: { name: form.legal_name, email: form.email } });
      await confirm.submit({ team: props.team, amount: amount.value, gateway: order.gateway,
        razorpay_order_id: resp.razorpay_order_id, razorpay_payment_id: resp.razorpay_payment_id, razorpay_signature: resp.razorpay_signature });
      emit('success'); show.value = false;
    } else if (order.adapter_key === 'stripe') {
      // Hosted Stripe Checkout — leave the SPA; /billing/credits confirms on return.
      window.location.href = order.checkout_url;
      return;
    } else {
      throw new Error(`Unsupported payment gateway: ${order.adapter_key}`);
    }
  } catch (e) { error.value = e.messages?.[0] || e.message || String(e); } finally { loading.value = false; }
}
</script>
