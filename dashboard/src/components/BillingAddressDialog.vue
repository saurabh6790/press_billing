<template>
  <Dialog v-model="show" :options="{ title: 'Billing address & GST', size: 'xl' }">
    <template #body-content>
      <BillingFields :fields="form" />
      <ErrorMessage class="mt-2" :message="error" />
    </template>
    <template #actions>
      <Button variant="solid" theme="gray" :loading="loading" @click="save">Save</Button>
    </template>
  </Dialog>
</template>
<script setup>
import { reactive, ref, computed, watch } from 'vue';
import { Dialog, Button, ErrorMessage, createResource } from 'frappe-ui';
import BillingFields from './BillingFields.vue';
const props = defineProps({ modelValue: Boolean, team: String, profile: Object });
const emit = defineEmits(['update:modelValue', 'success']);
const show = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) });
const form = reactive({ legal_name: '', gstin: '', email: '', phone: '', address_line1: '', city: '', state: '', pincode: '' });
watch(() => props.profile, (p) => p && Object.assign(form, p), { immediate: true });
const error = ref(''); const loading = ref(false);
const res = createResource({ url: 'billing.api.dashboard.save_billing_profile' });
async function save() {
  error.value = ''; loading.value = true;
  try { await res.submit({ team: props.team, ...form }); emit('success'); show.value = false; }
  catch (e) { error.value = e.messages?.[0] || String(e); } finally { loading.value = false; }
}
</script>
