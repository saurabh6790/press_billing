<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-lg font-semibold text-ink-gray-9">Catalog</h1>
      <p class="mt-0.5 text-sm text-ink-gray-6">Products and infrastructure — plans, add-ons and the regions teams run in.</p>
    </div>

    <section>
      <h2 class="mb-2 text-base font-semibold text-ink-gray-9">Plans</h2>
      <div class="overflow-hidden rounded-lg border border-outline-gray-2">
        <table class="w-full text-sm">
          <thead><tr class="border-b border-outline-gray-2 bg-surface-gray-1 text-left text-ink-gray-5">
            <th class="px-4 py-2 font-normal">Plan</th><th class="px-4 py-2 font-normal">Cycle</th>
            <th class="px-4 py-2 font-normal">Active</th><th class="px-4 py-2 text-right font-normal">Base Rate (INR)</th>
            <th class="px-4 py-2 text-right font-normal">Resources</th>
          </tr></thead>
          <tbody>
            <tr v-for="p in cat.data?.plans || []" :key="p.name" class="border-b border-outline-gray-1 last:border-0">
              <td class="px-4 py-2 font-medium text-ink-gray-8">{{ p.title || p.name }}</td>
              <td class="px-4 py-2 capitalize text-ink-gray-7">{{ p.billing_cycle }}</td>
              <td class="px-4 py-2"><Badge variant="subtle" :theme="p.is_active ? 'green' : 'gray'" :label="p.is_active ? 'Active' : 'Inactive'" /></td>
              <td class="px-4 py-2 text-right text-ink-gray-8">{{ money(p.inr_rate) }}</td>
              <td class="px-4 py-2 text-right text-ink-gray-7">{{ p.active_resources }}</td>
            </tr>
            <tr v-if="!(cat.data?.plans || []).length"><td colspan="5" class="px-4 py-6 text-center text-ink-gray-5">No plans.</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <section>
      <h2 class="mb-2 text-base font-semibold text-ink-gray-9">Add-ons</h2>
      <div class="overflow-hidden rounded-lg border border-outline-gray-2">
        <table class="w-full text-sm">
          <thead><tr class="border-b border-outline-gray-2 bg-surface-gray-1 text-left text-ink-gray-5">
            <th class="px-4 py-2 font-normal">Add-on</th><th class="px-4 py-2 font-normal">Resource</th>
            <th class="px-4 py-2 font-normal">Unit</th><th class="px-4 py-2 font-normal">Billing</th>
          </tr></thead>
          <tbody>
            <tr v-for="a in cat.data?.addons || []" :key="a.name" class="border-b border-outline-gray-1 last:border-0">
              <td class="px-4 py-2 font-medium text-ink-gray-8">{{ a.title || a.name }}</td>
              <td class="px-4 py-2 capitalize text-ink-gray-7">{{ a.resource_type }}</td>
              <td class="px-4 py-2 text-ink-gray-7">{{ a.unit }}</td>
              <td class="px-4 py-2 capitalize text-ink-gray-7">{{ a.billing_type }}</td>
            </tr>
            <tr v-if="!(cat.data?.addons || []).length"><td colspan="4" class="px-4 py-6 text-center text-ink-gray-5">No add-ons.</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <section>
      <h2 class="mb-2 text-base font-semibold text-ink-gray-9">Clusters</h2>
      <div class="overflow-hidden rounded-lg border border-outline-gray-2">
        <table class="w-full text-sm">
          <thead><tr class="border-b border-outline-gray-2 bg-surface-gray-1 text-left text-ink-gray-5">
            <th class="px-4 py-2 font-normal">Cluster</th><th class="px-4 py-2 text-right font-normal">Resources</th>
            <th class="px-4 py-2 text-right font-normal">Teams</th>
          </tr></thead>
          <tbody>
            <tr v-for="c in cat.data?.clusters || []" :key="c.cluster" class="border-b border-outline-gray-1 last:border-0">
              <td class="px-4 py-2 font-medium text-ink-gray-8">{{ c.cluster }}</td>
              <td class="px-4 py-2 text-right text-ink-gray-7">{{ c.resources }}</td>
              <td class="px-4 py-2 text-right text-ink-gray-7">{{ c.teams }}</td>
            </tr>
            <tr v-if="!(cat.data?.clusters || []).length"><td colspan="3" class="px-4 py-6 text-center text-ink-gray-5">No clusters.</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
<script setup>
import { Badge, createResource } from 'frappe-ui';
import { money } from '../utils';
const cat = createResource({ url: 'billing.api.admin.get_catalog', auto: true });
</script>
