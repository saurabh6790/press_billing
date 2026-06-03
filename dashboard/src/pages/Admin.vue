<template>
  <div class="space-y-6">
    <h1 class="text-xl font-semibold">Admin · Billing</h1>
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div class="rounded-lg border border-gray-200 bg-white p-5">
        <p class="text-sm text-gray-500">Total billed</p>
        <p class="mt-1 text-2xl font-semibold">{{ money(summary.data?.total_billed) }}</p>
      </div>
      <div class="rounded-lg border border-gray-200 bg-white p-5">
        <p class="text-sm text-gray-500">Collected</p>
        <p class="mt-1 text-2xl font-semibold text-green-600">{{ money(summary.data?.total_collected) }}</p>
      </div>
      <div class="rounded-lg border border-gray-200 bg-white p-5">
        <p class="text-sm text-gray-500">Outstanding</p>
        <p class="mt-1 text-2xl font-semibold text-amber-600">{{ money(summary.data?.outstanding) }}</p>
      </div>
    </div>
    <div class="grid grid-cols-1 gap-6 sm:grid-cols-2">
      <div>
        <h2 class="mb-2 text-base font-medium">Spend by cluster</h2>
        <div class="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <table class="w-full text-sm">
            <tbody>
              <tr v-for="c in clusters.data || []" :key="c.cluster" class="border-t border-gray-100 first:border-t-0">
                <td class="px-4 py-2">{{ c.cluster }}</td><td class="px-4 py-2 text-right">{{ money(c.amount) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div>
        <h2 class="mb-2 text-base font-medium">Free / trial subsidy</h2>
        <div class="rounded-lg border border-gray-200 bg-white p-5">
          <p class="text-2xl font-semibold">{{ money(subsidy.data?.total_subsidy) }}</p>
          <p class="mt-1 text-xs text-gray-500">true cost of non-paying teams (cost_report)</p>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import { createResource } from 'frappe-ui';
const summary = createResource({ url: 'press_billing.admin.get_summary', auto: true });
const clusters = createResource({ url: 'press_billing.admin.get_cluster_breakdown', auto: true });
const subsidy = createResource({ url: 'press_billing.admin.get_free_trial_costs', auto: true });
const money = (v) => '₹ ' + Number(v || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 });
</script>
