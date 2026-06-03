<template>
  <div class="max-w-3xl space-y-6">
    <h1 class="text-xl font-semibold text-ink-gray-9">New Subscription</h1>

    <section class="rounded-lg border border-outline-gray-2 bg-surface-white p-5 space-y-4">
      <h2 class="text-base font-medium text-ink-gray-8">1 · Choose a plan</h2>
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <button v-for="p in plans.data || []" :key="p.name" type="button"
          class="rounded-lg border p-4 text-left"
          :class="plan === p.name ? 'border-outline-gray-4 bg-surface-gray-2' : 'border-outline-gray-2 bg-surface-white hover:bg-surface-gray-1'"
          @click="plan = p.name">
          <p class="font-medium text-ink-gray-9">{{ p.title }}</p>
          <p class="mt-1 text-lg font-semibold text-ink-gray-9">{{ money(p.rate) }}<span class="text-xs font-normal text-ink-gray-5">/{{ p.billing_cycle }}</span></p>
        </button>
      </div>
    </section>

    <section class="rounded-lg border border-outline-gray-2 bg-surface-white p-5 space-y-4">
      <h2 class="text-base font-medium text-ink-gray-8">2 · Billing details</h2>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FormControl type="text" label="Legal name" v-model="profile.legal_name" />
        <FormControl type="text" label="GSTIN" v-model="profile.gstin" placeholder="27AAPFU0939F1ZV" />
        <FormControl type="text" label="Billing email" v-model="profile.email" />
        <FormControl type="text" label="Phone" v-model="profile.phone" />
        <FormControl type="text" label="Address line 1" v-model="profile.address_line1" />
        <FormControl type="text" label="City" v-model="profile.city" />
        <FormControl type="text" label="State" v-model="profile.state" />
        <FormControl type="text" label="Pincode" v-model="profile.pincode" />
      </div>
    </section>

    <div class="flex items-center gap-3">
      <Button variant="solid" theme="gray" :loading="loading" @click="submit">Subscribe</Button>
      <Badge v-if="done" theme="green" variant="subtle" :label="`Subscribed: ${done}`" />
      <ErrorMessage :message="error" />
    </div>
  </div>
</template>
<script setup>
import { ref, reactive } from 'vue';
import { Button, FormControl, Badge, ErrorMessage, createResource } from 'frappe-ui';
import { money } from '../utils';
const team = ref(null);
createResource({ url: 'press_billing.dashboard.whoami', auto: true, onSuccess: (d) => (team.value = d.team) });
const plans = createResource({ url: 'press_billing.dashboard.list_plans', auto: true, params: { currency: 'INR' } });
const plan = ref(null);
const profile = reactive({ legal_name: '', gstin: '', email: '', phone: '', address_line1: '', city: '', state: '', pincode: '' });
const loading = ref(false); const error = ref(''); const done = ref('');
const saveProfile = createResource({ url: 'press_billing.dashboard.save_billing_profile' });
const subscribe = createResource({ url: 'press_billing.dashboard.create_subscription' });
async function submit() {
  error.value = ''; done.value = ''; loading.value = true;
  try {
    await saveProfile.submit({ team: team.value, ...profile });
    const r = await subscribe.submit({ team: team.value, plan: plan.value, cluster: 'ap-south-1' });
    done.value = r.subscription;
  } catch (e) { error.value = e.messages?.[0] || String(e); } finally { loading.value = false; }
}
</script>
