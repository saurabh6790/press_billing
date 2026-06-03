<template>
  <div class="space-y-4">
    <h1 class="text-xl font-semibold">Payment Methods</h1>
    <div class="space-y-2">
      <div v-for="m in methods.data || []" :key="m.name" class="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3">
        <div>
          <span class="font-medium">{{ m.display_label || m.method_type }}</span>
          <Badge v-if="m.is_default" theme="blue" label="Default" class="ml-2" />
          <span v-if="m.expiry_month" class="ml-2 text-xs text-gray-500">exp {{ m.expiry_month }}/{{ m.expiry_year }}</span>
        </div>
        <Badge :theme="m.status === 'active' ? 'green' : 'gray'" :label="m.status" />
      </div>
      <p v-if="!(methods.data || []).length" class="text-gray-500">No payment methods on file.</p>
    </div>
  </div>
</template>
<script setup>
import { Badge, createResource } from 'frappe-ui';
const methods = createResource({ url: 'press_billing.dashboard.list_payment_methods', auto: true });
</script>
