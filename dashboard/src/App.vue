<template>
  <div class="min-h-screen bg-gray-50 text-gray-900">
    <header class="border-b border-gray-200 bg-white">
      <div class="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <div class="flex items-center gap-2">
          <span class="text-lg font-semibold">Cloud Billing</span>
          <Badge theme="blue" label="v2" />
        </div>
        <nav class="flex gap-1">
          <router-link
            v-for="tab in tabs"
            :key="tab.to"
            :to="tab.to"
            class="rounded px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100"
            active-class="bg-gray-100 text-gray-900"
          >
            {{ tab.label }}
          </router-link>
        </nav>
      </div>
    </header>
    <main class="mx-auto max-w-5xl px-6 py-8">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { Badge } from 'frappe-ui';

const tabs = [
  { label: 'Overview', to: '/billing' },
  { label: 'Invoices', to: '/billing/invoices' },
  { label: 'Payment Methods', to: '/billing/methods' },
  { label: 'Credits', to: '/billing/credits' },
  { label: 'Admin', to: '/billing/admin' },
];
</script>
