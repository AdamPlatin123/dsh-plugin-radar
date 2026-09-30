<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { meta } from '../lib/data'

const { t } = useI18n()
const items = computed(() => {
  const s = meta.stats
  return [
    { key: 'ok', n: s.ok, cls: 'v-ok' },
    { key: 'incompatible', n: s.incompatible, cls: 'v-incompatible' },
    { key: 'pending', n: s.pending, cls: 'v-pending' },
    { key: 'untested', n: s.untested, cls: 'v-untested' },
  ]
})
</script>

<template>
  <div class="strip">
    <div class="total">
      <div class="num n">{{ (meta.totalListed).toLocaleString() }}</div>
      <div class="lbl">{{ t('stat.total') }}</div>
    </div>
    <div v-for="it in items" :key="it.key" class="cell" :class="it.cls">
      <div class="num n">{{ it.n.toLocaleString() }}</div>
      <div class="lbl">{{ t(`stat.${it.key}`) }}</div>
    </div>
  </div>
</template>

<style scoped>
.strip {
  display: grid; grid-template-columns: 1.4fr repeat(4, 1fr); gap: 1px;
  background: var(--line-soft); border: 1px solid var(--line-soft);
  border-radius: var(--radius); overflow: hidden;
}
.cell, .total { background: var(--panel); padding: 14px 16px; text-align: center; }
.n { font-size: 24px; color: var(--tone, var(--cy)); }
.total .n { font-size: 30px; color: var(--cy); }
.lbl { font-size: 12px; color: var(--fg-dim); margin-top: 2px; }

@media (max-width: 640px) {
  .strip { grid-template-columns: repeat(2, 1fr); }
  .total { grid-column: span 2; }
}
</style>
