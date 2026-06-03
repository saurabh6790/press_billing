<template>
  <Dialog v-model="show" :options="{ title: 'Add a card' }">
    <template #body-content>
      <div class="space-y-4">
        <p class="rounded-md bg-surface-gray-2 px-3 py-2 text-xs text-ink-gray-6">
          In production the card number is collected by the gateway's secure field (PCI) and tokenised client-side. This demo records the display details.
        </p>
        <FormControl type="text" label="Cardholder / label" v-model="label" placeholder="Visa ····4242" />
        <div class="flex gap-3">
          <FormControl type="number" label="Exp. month" v-model="month" class="w-28" />
          <FormControl type="number" label="Exp. year" v-model="year" class="w-32" />
        </div>
        <ErrorMessage :message="error" />
      </div>
    </template>
    <template #actions>
      <Button variant="solid" theme="gray" :loading="loading" @click="submit">Add card</Button>
    </template>
  </Dialog>
</template>
<script setup>
import { ref, computed } from 'vue';
import { Dialog, Button, FormControl, ErrorMessage, createResource } from 'frappe-ui';
const props = defineProps({ modelValue: Boolean, team: String, gateway: String });
const emit = defineEmits(['update:modelValue', 'success']);
const show = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) });
const label = ref('Visa ····4242'); const month = ref(12); const year = ref(2030);
const error = ref(''); const loading = ref(false);
const res = createResource({ url: 'press_billing.dashboard.add_demo_card' });
async function submit() {
  error.value = ''; loading.value = true;
  try {
    await res.submit({ team: props.team, gateway: props.gateway, display_label: label.value, expiry_month: month.value, expiry_year: year.value });
    emit('success'); show.value = false;
  } catch (e) { error.value = e.messages?.[0] || String(e); } finally { loading.value = false; }
}
</script>
