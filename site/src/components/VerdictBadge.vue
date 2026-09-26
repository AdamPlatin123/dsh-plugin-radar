<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ verdict: string; dim?: boolean }>()
const { t } = useI18n()
const label = computed(() => t(`stat.${props.verdict}`) || props.verdict)
</script>

<template>
  <span class="badge" :class="`v-${verdict}`" :data-dim="dim || undefined">
    <span class="dot"></span>{{ label }}
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 2px 10px; border-radius: 999px;
  font-size: 12px; line-height: 1.6;
  color: var(--tone, var(--fg-dim));
  background: var(--tone-dim, var(--skip-dim));
  border: 1px solid var(--tone, var(--line));
  white-space: nowrap;
}
.badge[data-dim] { opacity: 0.65; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: var(--tone, var(--fg-dim)); }
</style>
