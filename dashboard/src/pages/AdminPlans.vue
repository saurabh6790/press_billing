<template>
  <div class="space-y-4">
    <div>
      <h1 class="text-lg font-semibold text-ink-gray-9">Plan Consumption</h1>
      <p class="mt-0.5 text-sm text-ink-gray-6">Active resources and monthly run-rate per plan, highest first (INR-equivalent).</p>
    </div>
    <Panel title="" :rows="plan.data" :cols="['Plan', 'Resources', 'Monthly Run-rate']" :fields="['plan', 'resources', 'monthly']" money-field="monthly" />
  </div>
</template>
<script setup>
import { createResource } from 'frappe-ui';
import Panel from '../components/Panel.vue';
const plan = createResource({ url: 'billing.api.admin.get_plan_consumption', auto: true });
</script>
