<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-base font-semibold text-ink-gray-9">Cards & mandates</p>
        <p class="text-xs text-ink-gray-5">
          We charge your primary method first; if it fails we automatically try your backups in order.
        </p>
      </div>
      <Button variant="solid" theme="gray" label="Add payment method" @click="add = true" />
    </div>

    <div class="divide-y divide-outline-gray-1">
      <div
        v-for="(m, i) in list"
        :key="m.name"
        class="flex items-center justify-between py-4"
      >
        <div class="flex items-center gap-3">
          <span class="w-6 text-center text-xs font-medium text-ink-gray-5">{{ i + 1 }}</span>
          <component
            :is="m.method_type === 'card' ? LucideCreditCard : LucideSmartphone"
            class="size-5 text-ink-gray-5"
          />
          <div>
            <p class="font-medium text-ink-gray-8">
              {{ m.display_label || m.method_type }}
              <Badge v-if="i === 0" theme="blue" variant="subtle" label="Primary" class="ml-1" />
              <Badge v-else theme="gray" variant="subtle" :label="`Backup ${i}`" class="ml-1" />
              <Badge v-if="m.reauth_required" theme="orange" variant="subtle" label="Re-auth needed" class="ml-1" />
            </p>
            <p v-if="m.expiry_month" class="text-xs text-ink-gray-5">
              expires {{ m.expiry_month }}/{{ m.expiry_year }}
            </p>
          </div>
        </div>

        <div class="flex items-center gap-1">
          <Button variant="ghost" :disabled="i === 0 || busy" @click="moveUp(i)" aria-label="Move up">
            <template #icon><LucideChevronUp class="size-4" /></template>
          </Button>
          <Button variant="ghost" :disabled="i === list.length - 1 || busy" @click="moveDown(i)" aria-label="Move down">
            <template #icon><LucideChevronDown class="size-4" /></template>
          </Button>
          <Button
            v-if="i !== 0 && m.status === 'active'"
            label="Make primary"
            :disabled="busy"
            @click="makePrimary(m.name)"
          />
          <Button theme="red" variant="subtle" label="Remove" :disabled="busy" @click="remove(m.name)" />
        </div>
      </div>
      <p v-if="!list.length" class="py-6 text-ink-gray-5">No payment methods on file.</p>
    </div>

    <AddCardDialog
      v-model="add"
      :team="store.team"
      :hasProfile="!!profile.data?.legal_name"
      @success="methods.reload()"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { Badge, Button, createResource } from 'frappe-ui';
import LucideCreditCard from '~icons/lucide/credit-card';
import LucideSmartphone from '~icons/lucide/smartphone';
import LucideChevronUp from '~icons/lucide/chevron-up';
import LucideChevronDown from '~icons/lucide/chevron-down';
import { store } from '../store';
import AddCardDialog from '../components/AddCardDialog.vue';

const add = ref(false);
const methods = createResource({ url: 'billing.dashboard.list_payment_methods', makeParams: () => ({ team: store.team }) });
const profile = createResource({ url: 'billing.dashboard.get_billing_profile', makeParams: () => ({ team: store.team }) });
watch(() => store.team, (t) => { if (t) { methods.reload(); profile.reload(); } }, { immediate: true });

// API returns methods already ordered by priority (primary first).
const list = computed(() => methods.data || []);

const removeRes = createResource({ url: 'billing.dashboard.remove_payment_method', onSuccess: () => methods.reload() });
const primaryRes = createResource({ url: 'billing.dashboard.set_default_payment_method', onSuccess: () => methods.reload() });
const reorderRes = createResource({ url: 'billing.dashboard.reorder_payment_methods', onSuccess: () => methods.reload() });
const busy = computed(() => reorderRes.loading || primaryRes.loading || removeRes.loading);

function remove(name) { removeRes.submit({ payment_method: name }); }
function makePrimary(name) { primaryRes.submit({ payment_method: name }); }

function reorderTo(names) {
  reorderRes.submit({ team: store.team, ordered: JSON.stringify(names) });
}
function moveUp(i) {
  const names = list.value.map((m) => m.name);
  [names[i - 1], names[i]] = [names[i], names[i - 1]];
  reorderTo(names);
}
function moveDown(i) {
  const names = list.value.map((m) => m.name);
  [names[i + 1], names[i]] = [names[i], names[i + 1]];
  reorderTo(names);
}
</script>
