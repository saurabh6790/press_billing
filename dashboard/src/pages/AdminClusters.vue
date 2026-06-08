<template>
  <div class="space-y-4">
    <div>
      <h1 class="text-lg font-semibold text-ink-gray-9">Cluster Consumption</h1>
      <p class="mt-0.5 text-sm text-ink-gray-6">Active resources and monthly run-rate per region (INR-equivalent).</p>
    </div>
    <Panel title="" :rows="cluster.data" :cols="['Cluster', 'Resources', 'Monthly Run-rate']" :fields="['cluster', 'resources', 'monthly']" money-field="monthly" />
  </div>
</template>
<script setup>
import { createResource } from 'frappe-ui';
import Panel from '../components/Panel.vue';
const cluster = createResource({ url: 'billing.api.admin.get_cluster_consumption', auto: true });
</script>
