<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { meta, STAR_BUCKETS, type Filters } from '../lib/data'

const props = defineProps<{ modelValue: Filters }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: Filters): void }>()
const { t } = useI18n()

const VERDICTS = ['ok', 'incompatible', 'pending', 'untested', 'gone', 'ambiguous', 'unlocated']

function set(patch: Partial<Filters>) {
  emit('update:modelValue', { ...props.modelValue, ...patch })
}
let qTimer: ReturnType<typeof setTimeout> | undefined
function setQ(v: string) {
  clearTimeout(qTimer)
  qTimer = setTimeout(() => set({ q: v }), 150)   // 搜索防抖 150ms
}
</script>

<template>
  <div class="bar">
    <select class="sel" :value="modelValue.domain" @change="set({ domain: ($event.target as HTMLSelectElement).value })">
      <option value="all">{{ t('filter.all') }}</option>
      <option v-for="d in meta.domains" :key="d.slug" :value="d.slug">{{ d.title }}</option>
    </select>
    <select class="sel" :value="modelValue.verdict" @change="set({ verdict: ($event.target as HTMLSelectElement).value })">
      <option value="all">{{ t('filter.verdict') }} · {{ t('filter.any') }}</option>
      <option v-for="v in VERDICTS" :key="v" :value="v">{{ t(`stat.${v}`) }}</option>
    </select>
    <select class="sel" :value="modelValue.stars" @change="set({ stars: ($event.target as HTMLSelectElement).value })">
      <option value="all">{{ t('filter.stars') }} · {{ t('filter.any') }}</option>
      <option v-for="b in STAR_BUCKETS" :key="b.key" :value="b.key">★ {{ b.key }}</option>
    </select>
    <input
      class="q" type="search" :placeholder="t('filter.search')"
      :value="modelValue.q" @input="setQ(($event.target as HTMLInputElement).value)"
    />
  </div>
</template>

<style scoped>
.bar { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
.sel, .q {
  background: var(--panel); border: 1px solid var(--line); color: var(--fg);
  border-radius: var(--radius-s); padding: 8px 12px; font-size: 14px; outline: none;
}
.sel { cursor: pointer; }
.q { flex: 1; min-width: 200px; }
.sel:focus, .q:focus { border-color: var(--cy); }
</style>
