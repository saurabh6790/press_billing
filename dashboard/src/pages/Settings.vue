<template>
  <div class="max-w-xl space-y-5">
    <h1 class="text-xl font-semibold text-ink-gray-9">Billing Settings</h1>
    <section class="rounded-lg border border-outline-gray-2 bg-surface-white p-5 space-y-4">
      <FormControl type="select" label="Payment mode" v-model="mode"
        :options="[{ label: 'Postpaid (invoice in arrears)', value: 'postpaid' }, { label: 'Prepaid (wallet)', value: 'prepaid' }]" />
      <FormControl v-if="mode === 'prepaid'" type="number" label="Minimum balance (₹)" v-model="minBalance" />
      <FormControl v-if="mode === 'postpaid'" type="number" label="Spend alert threshold (₹)" v-model="threshold" />
      <p class="text-xs text-ink-gray-5">Mode changes take effect at the next billing period.</p>
      <div class="flex items-center gap-3">
        <Button variant="solid" theme="gray" :loading="loading" @click="save">Save</Button>
        <Badge v-if="saved" theme="green" variant="subtle" label="Saved" />
      </div>
    </section>
  </div>
</template>
<script setup>
import { ref } from 'vue';
import { Button, FormControl, Badge, createResource } from 'frappe-ui';
const team = ref(null); const mode = ref('postpaid'); const minBalance = ref(0); const threshold = ref(0);
const loading = ref(false); const saved = ref(false);
createResource({ url: 'press_billing.dashboard.whoami', auto: true, onSuccess: (d) => { team.value = d.team; settings.reload(); } });
const settings = createResource({ url: 'press_billing.dashboard.get_billing_settings', auto: false,
  onSuccess: (d) => { mode.value = d.billing_mode; minBalance.value = d.min_balance; threshold.value = d.spend_alert_threshold; } });
const res = createResource({ url: 'press_billing.dashboard.save_billing_settings' });
async function save() {
  loading.value = true; saved.value = false;
  try { await res.submit({ team: team.value, billing_mode: mode.value, min_balance: minBalance.value, spend_alert_threshold: threshold.value }); saved.value = true; }
  finally { loading.value = false; }
}
</script>
