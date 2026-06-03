<template>
  <div class="rounded-lg border border-outline-gray-2 bg-surface-white p-5">
    <p class="text-sm text-ink-gray-6">{{ label }}</p>
    <p class="mt-1 text-2xl font-semibold" :class="valueClass">{{ value }}</p>
    <p v-if="sub" class="mt-1 text-xs text-ink-gray-5">{{ sub }}</p>
    <div v-if="$slots.action" class="mt-3"><slot name="action" /></div>
  </div>
</template>
<script setup>
defineProps({ label: String, value: [String, Number], sub: String, valueClass: String });
</script>
