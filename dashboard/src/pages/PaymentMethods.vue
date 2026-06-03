<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-ink-gray-9">Payment Methods</h1>
      <Button variant="solid" theme="gray" @click="add = true">Add Card</Button>
    </div>
    <div class="space-y-2">
      <div v-for="m in methods.data || []" :key="m.name" class="flex items-center justify-between rounded-lg border border-outline-gray-2 bg-surface-white px-4 py-3">
        <div class="flex items-center gap-2">
          <span class="font-medium text-ink-gray-8">{{ m.display_label || m.method_type }}</span>
          <Badge v-if="m.is_default" theme="blue" variant="subtle" label="Default" />
          <span v-if="m.expiry_month" class="text-xs text-ink-gray-5">exp {{ m.expiry_month }}/{{ m.expiry_year }}</span>
        </div>
        <Badge variant="subtle" :theme="m.status === 'active' ? 'green' : 'gray'" :label="m.status" />
      </div>
      <p v-if="!(methods.data || []).length" class="text-ink-gray-5">No payment methods on file.</p>
    </div>
    <AddCardDialog v-model="add" :team="team" :gateway="gateway" @success="methods.reload()" />
  </div>
</template>
<script setup>
import { ref } from 'vue';
import { Badge, Button, createResource } from 'frappe-ui';
import AddCardDialog from '../components/AddCardDialog.vue';
const add = ref(false); const team = ref(null); const gateway = ref('GW-Demo-Stripe');
createResource({ url: 'press_billing.dashboard.whoami', auto: true, onSuccess: (d) => (team.value = d.team) });
const methods = createResource({ url: 'press_billing.dashboard.list_payment_methods', auto: true });
</script>
