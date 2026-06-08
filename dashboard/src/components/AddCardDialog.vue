<template>
  <Dialog v-model="show" :options="{ title: 'Add payment method', size: 'xl' }">
    <template #body-content>
      <div class="space-y-4">
        <!-- Razorpay: card vs UPI Autopay choice -->
        <div v-if="isRazorpay" class="grid grid-cols-2 gap-3">
          <button
            type="button"
            class="rounded-md border px-3 py-3 text-left transition"
            :class="method === 'card' ? 'border-outline-gray-4 bg-surface-gray-2' : 'border-outline-gray-2'"
            @click="method = 'card'"
          >
            <p class="text-sm font-medium text-ink-gray-8">Card</p>
            <p class="text-xs text-ink-gray-5">Auto-charged each month. No recurring limit.</p>
          </button>
          <button
            type="button"
            class="rounded-md border px-3 py-3 text-left transition"
            :class="[
              method === 'upi_autopay' ? 'border-outline-gray-4 bg-surface-gray-2' : 'border-outline-gray-2',
              !allowUpi ? 'cursor-not-allowed opacity-50' : '',
            ]"
            :disabled="!allowUpi"
            @click="allowUpi && (method = 'upi_autopay')"
          >
            <p class="text-sm font-medium text-ink-gray-8">UPI Autopay</p>
            <p class="text-xs text-ink-gray-5">Mandate via your bank. Capped at ₹1,00,000/charge.</p>
          </button>
        </div>

        <div
          v-if="isRazorpay && !allowUpi && options.data?.upi_block_reason"
          class="rounded-md bg-surface-amber-1 px-3 py-2 text-xs text-ink-amber-3"
        >
          {{ options.data.upi_block_reason }}
        </div>

        <div class="rounded-md bg-surface-gray-2 px-3 py-2 text-xs text-ink-gray-6">{{ blurb }}</div>

        <!-- Stripe: card details via Stripe Elements (PCI — we never see the PAN) -->
        <div v-if="isStripe">
          <p class="mb-1 text-sm font-medium text-ink-gray-8">Card details</p>
          <div ref="cardEl" class="rounded-md border border-outline-gray-2 px-3 py-3"></div>
        </div>

        <div v-if="!hasProfile">
          <p class="mb-2 text-sm font-medium text-ink-gray-8">Billing details</p>
          <BillingFields :fields="form" />
        </div>
        <ErrorMessage :message="error" />
      </div>
    </template>
    <template #actions>
      <Button variant="solid" theme="gray" :loading="loading" :disabled="!options.data?.gateway" @click="submit">
        {{ cta }}
      </Button>
    </template>
  </Dialog>
</template>
<script setup>
import { reactive, ref, computed, watch, nextTick } from 'vue';
import { Dialog, Button, ErrorMessage, createResource } from 'frappe-ui';
import BillingFields from './BillingFields.vue';
import { openRazorpay, loadStripeJs } from '../utils';

const props = defineProps({ modelValue: Boolean, team: String, hasProfile: Boolean });
const emit = defineEmits(['update:modelValue', 'success']);
const show = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) });
const form = reactive({ legal_name: '', gstin: '', email: '', phone: '', address_line1: '', city: '', state: '', pincode: '' });
const error = ref(''); const loading = ref(false);
const method = ref('card');

// Stripe Elements state.
const cardEl = ref(null);
let stripe = null; let elements = null; let cardElement = null;
let cardBrand = 'card';

const options = createResource({
  url: 'billing.api.dashboard.get_payment_method_options',
  makeParams: () => ({ team: props.team }),
  onSuccess: (d) => { method.value = d.allow_upi ? 'upi_autopay' : 'card'; },
});

const adapter = computed(() => options.data?.adapter_key);
const isRazorpay = computed(() => adapter.value === 'razorpay');
const isStripe = computed(() => adapter.value === 'stripe');
const allowUpi = computed(() => !!options.data?.allow_upi);
const blurb = computed(() => {
  if (isStripe.value) return 'Add a card via Stripe. Your card is tokenised by Stripe — we never see the number.';
  if (method.value === 'upi_autopay')
    return 'Authorise a UPI Autopay mandate through Razorpay Checkout. The mandate ceiling equals your trust-tier cap; your bank approves it — we never see the instrument.';
  return 'Authorise a card through Razorpay Checkout so we can auto-charge invoices. Your bank tokenises it — we never see the card number.';
});
const cta = computed(() => {
  if (loading.value) return 'Working…';
  return isStripe.value ? 'Add card' : 'Set up with Razorpay';
});

watch(show, async (v) => {
  if (v && props.team) {
    await options.reload();
    if (isStripe.value) await mountStripe();
  } else {
    teardownStripe();
  }
});

async function mountStripe() {
  if (!options.data?.publishable_key) return;
  await nextTick();
  if (!cardEl.value) return;
  stripe = await loadStripeJs(options.data.publishable_key);
  elements = stripe.elements();
  cardElement = elements.create('card', { hidePostalCode: true });
  cardElement.mount(cardEl.value);
  cardElement.on('change', (ev) => { cardBrand = ev.brand && ev.brand !== 'unknown' ? ev.brand : 'card'; });
}
function teardownStripe() {
  if (cardElement) { cardElement.unmount(); cardElement = null; }
  elements = null; stripe = null; cardBrand = 'card';
}

const saveProfile = createResource({ url: 'billing.api.dashboard.save_billing_profile' });
const setup = createResource({ url: 'billing.api.dashboard.setup_payment_method_order' });
const confirm = createResource({ url: 'billing.api.dashboard.confirm_payment_method_order' });
const initStripe = createResource({ url: 'billing.api.dashboard.initiate_card_setup' });
const confirmStripe = createResource({ url: 'billing.api.dashboard.confirm_card' });

async function submit() {
  error.value = ''; loading.value = true;
  try {
    if (!props.hasProfile) await saveProfile.submit({ team: props.team, ...form });
    if (isStripe.value) await submitStripe();
    else await submitRazorpay();
    emit('success'); show.value = false; teardownStripe();
  } catch (e) { error.value = e.messages?.[0] || e.message || String(e); } finally { loading.value = false; }
}

async function submitRazorpay() {
  const order = await setup.submit({ team: props.team, gateway: options.data.gateway, method_type: method.value });
  const desc = method.value === 'upi_autopay' ? 'UPI Autopay mandate' : 'Card mandate';
  const resp = await openRazorpay({ key: order.key_id, order_id: order.order_id, amount: order.amount || 100,
    description: desc, prefill: { name: form.legal_name, email: form.email } });
  await confirm.submit({ payment_method: order.payment_method, razorpay_payment_id: resp.razorpay_payment_id,
    razorpay_order_id: resp.razorpay_order_id, razorpay_signature: resp.razorpay_signature, razorpay_token_id: resp.razorpay_payment_id });
}

async function submitStripe() {
  if (!cardElement) throw new Error('Card form not ready');
  const order = await initStripe.submit({ team: props.team, gateway: options.data.gateway });
  const { error: stripeError, setupIntent } = await stripe.confirmCardSetup(order.client_secret, {
    payment_method: { card: cardElement, billing_details: { name: form.legal_name, email: form.email } },
  });
  if (stripeError) throw new Error(stripeError.message);
  await confirmStripe.submit({
    payment_method: order.payment_method,
    gateway_method_id: setupIntent.payment_method,
    display_label: `${cardBrand.charAt(0).toUpperCase() + cardBrand.slice(1)} card`,
  });
}
</script>
