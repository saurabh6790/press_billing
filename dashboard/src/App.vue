<template>
  <div class="min-h-screen bg-surface-gray-1 text-ink-gray-9">
    <header class="border-b border-outline-gray-2 bg-surface-white">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <div class="flex items-center gap-2">
          <span class="text-base font-semibold text-ink-gray-9">Cloud Billing</span>
          <Badge theme="blue" variant="subtle" label="v2" />
        </div>
        <nav class="flex items-center gap-1">
          <router-link
            v-for="tab in tabs" :key="tab.to" :to="tab.to"
            class="rounded px-3 py-1.5 text-sm text-ink-gray-6 hover:bg-surface-gray-2"
            active-class="!bg-surface-gray-3 !text-ink-gray-9 font-medium">
            {{ tab.label }}
          </router-link>
        </nav>
      </div>
    </header>
    <main class="mx-auto max-w-6xl px-6 py-6"><router-view /></main>
  </div>
</template>
<script setup>
import { Badge } from 'frappe-ui';
const tabs = [
  { label: 'Overview', to: '/billing' },
  { label: 'Subscribe', to: '/billing/subscribe' },
  { label: 'Invoices', to: '/billing/invoices' },
  { label: 'Payment Methods', to: '/billing/methods' },
  { label: 'Credits', to: '/billing/credits' },
  { label: 'Settings', to: '/billing/settings' },
  { label: 'Admin', to: '/billing/admin' },
];
</script>
