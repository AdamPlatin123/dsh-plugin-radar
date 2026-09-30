<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { meta } from '../lib/data'

const { t } = useI18n()
// 26h 阈值与 data-freshness.yml 断警口径一致
const fresh = computed(() => {
  const ts = Date.parse(meta.generatedAt.replace(/(\d{4}-\d{2}-\d{2})T/, '$1T'))
  return Date.now() - ts < 26 * 3600 * 1000
})
const short = computed(() => (meta.runId ? meta.runId.slice(0, 13) : ''))
</script>

<template>
  <span class="chip" :class="fresh ? 'ok' : 'warn'">
    <span class="pulse"></span>
    {{ fresh ? t('freshness.fresh') : t('freshness.stale') }} <span class="num rid">{{ short }}</span>
  </span>
</template>

<style scoped>
.chip {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 12px; padding: 3px 10px; border-radius: 999px;
  border: 1px solid var(--line); color: var(--fg-dim); white-space: nowrap;
}
.chip.ok { color: var(--ok); border-color: var(--ok-dim); background: var(--ok-dim); }
.chip.warn { color: var(--warn); border-color: var(--warn-dim); background: var(--warn-dim); }
.pulse { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.rid { font-size: 11px; opacity: 0.8; }

@media (max-width: 640px) { .rid { display: none; } }
</style>
