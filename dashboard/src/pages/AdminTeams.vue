<template>
  <div class="space-y-4">
    <div>
      <h1 class="text-lg font-semibold text-ink-gray-9">Teams</h1>
      <p class="mt-0.5 text-sm text-ink-gray-6">{{ filtered.length }} of {{ (teams.data || []).length }} teams · monetary columns INR-equivalent</p>
    </div>

    <!-- filters -->
    <div class="flex flex-wrap items-end gap-3">
      <div>
        <label class="mb-1 block text-xs text-ink-gray-5">Status</label>
        <FormControl type="select" v-model="fStatus" :options="statusOptions" />
      </div>
      <div>
        <label class="mb-1 block text-xs text-ink-gray-5">Tier</label>
        <FormControl type="select" v-model="fTier" :options="tierOptions" />
      </div>
      <div>
        <label class="mb-1 block text-xs text-ink-gray-5">Min MRR (₹)</label>
        <FormControl type="number" v-model="fMinMrr" placeholder="0" />
      </div>
      <label class="flex items-center gap-2 pb-2 text-sm text-ink-gray-7">
        <FormControl type="checkbox" v-model="fOpenOnly" /> Has open invoices
      </label>
      <Button v-if="dirty" variant="ghost" label="Clear" @click="clearFilters" />
      <FormControl class="ml-auto" type="text" v-model="fSearch" placeholder="Search team…" />
    </div>

    <div class="overflow-hidden rounded-lg border border-outline-gray-2">
      <table class="w-full text-sm">
        <thead><tr class="border-b border-outline-gray-2 bg-surface-gray-1 text-left text-ink-gray-5">
          <th class="px-4 py-2.5 font-normal">Team</th>
          <th class="px-4 py-2.5 font-normal cursor-pointer" @click="sortBy('tier')">Tier</th>
          <th class="px-4 py-2.5 font-normal">Status</th>
          <th class="px-4 py-2.5 text-right font-normal cursor-pointer" @click="sortBy('resources')">Resources</th>
          <th class="px-4 py-2.5 text-right font-normal cursor-pointer" @click="sortBy('mrr')">MRR{{ sortArrow('mrr') }}</th>
          <th class="px-4 py-2.5 text-right font-normal cursor-pointer" @click="sortBy('open_invoices')">Open{{ sortArrow('open_invoices') }}</th>
          <th class="px-4 py-2.5 text-right font-normal cursor-pointer" @click="sortBy('credit_balance')">Credit</th>
        </tr></thead>
        <tbody>
          <tr v-for="t in filtered" :key="t.team" class="cursor-pointer border-b border-outline-gray-1 last:border-0 hover:bg-surface-gray-1" @click="open(t)">
            <td class="px-4 py-3 font-medium text-ink-gray-8">{{ t.team }}</td>
            <td class="px-4 py-3 uppercase text-ink-gray-7">{{ t.tier }}</td>
            <td class="px-4 py-3"><Badge variant="subtle" :theme="standingTheme(t.standing)" :label="titleCase(t.standing)" /></td>
            <td class="px-4 py-3 text-right text-ink-gray-7">{{ t.resources }}</td>
            <td class="px-4 py-3 text-right font-medium text-ink-gray-8">{{ money(t.mrr) }}</td>
            <td class="px-4 py-3 text-right" :class="t.open_invoices ? 'text-ink-amber-3' : 'text-ink-gray-5'">{{ t.open_invoices }}</td>
            <td class="px-4 py-3 text-right text-ink-gray-7">{{ money(t.credit_balance) }}</td>
          </tr>
          <tr v-if="!filtered.length"><td colspan="7" class="px-4 py-8 text-center text-ink-gray-5">No teams match these filters.</td></tr>
        </tbody>
      </table>
    </div>
    <TeamDetailDialog v-model="show" :data="selected" />
  </div>
</template>
<script setup>
import { ref, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import { Badge, Button, FormControl, createResource } from 'frappe-ui';
import TeamDetailDialog from '../components/TeamDetailDialog.vue';
import { money, titleCase, standingTheme } from '../utils';

const route = useRoute();
const teams = createResource({ url: 'billing.admin.list_teams', auto: true });

const fStatus = ref('all');
const fTier = ref('all');
const fMinMrr = ref('');
const fOpenOnly = ref(false);
const fSearch = ref('');
const sortKey = ref('mrr');
const sortDir = ref('desc');

// Delinquent card drills in here with ?status=delinquent.
watch(() => route.query.status, (s) => { if (s) fStatus.value = String(s); }, { immediate: true });

const statusOptions = [
  { label: 'All statuses', value: 'all' },
  { label: 'Active', value: 'current' },
  { label: 'Past Due', value: 'past_due' },
  { label: 'Suspended', value: 'suspended' },
  { label: 'Delinquent (past due + suspended)', value: 'delinquent' },
];
const tierOptions = computed(() => [{ label: 'All tiers', value: 'all' },
  ...[...new Set((teams.data || []).map((t) => t.tier))].sort().map((t) => ({ label: String(t).toUpperCase(), value: t }))]);

const dirty = computed(() => fStatus.value !== 'all' || fTier.value !== 'all' || fMinMrr.value || fOpenOnly.value || fSearch.value);
function clearFilters() { fStatus.value = 'all'; fTier.value = 'all'; fMinMrr.value = ''; fOpenOnly.value = false; fSearch.value = ''; }

const filtered = computed(() => {
  let rows = (teams.data || []).filter((t) => {
    if (fStatus.value === 'delinquent' && !['past_due', 'suspended'].includes(t.standing)) return false;
    if (!['all', 'delinquent'].includes(fStatus.value) && t.standing !== fStatus.value) return false;
    if (fTier.value !== 'all' && t.tier !== fTier.value) return false;
    if (fMinMrr.value && t.mrr < Number(fMinMrr.value)) return false;
    if (fOpenOnly.value && !t.open_invoices) return false;
    if (fSearch.value && !t.team.toLowerCase().includes(fSearch.value.toLowerCase())) return false;
    return true;
  });
  const dir = sortDir.value === 'asc' ? 1 : -1;
  return [...rows].sort((a, b) => {
    const av = a[sortKey.value], bv = b[sortKey.value];
    return (av > bv ? 1 : av < bv ? -1 : 0) * dir;
  });
});

function sortBy(k) { if (sortKey.value === k) sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'; else { sortKey.value = k; sortDir.value = 'desc'; } }
function sortArrow(k) { return sortKey.value === k ? (sortDir.value === 'asc' ? ' ↑' : ' ↓') : ''; }

const show = ref(false); const selected = ref(null);
function open(t) { selected.value = t; show.value = true; }
</script>
