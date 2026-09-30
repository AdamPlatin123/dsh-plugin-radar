<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ text: string }>()
const { t } = useI18n()
const done = ref(false)

async function copy() {
  try {
    await navigator.clipboard.writeText(props.text)
    done.value = true
    setTimeout(() => (done.value = false), 1600)
  } catch {
    /* 剪贴板不可用时静默（HTTP 环境） */
  }
}
</script>

<template>
  <span class="wrap">
    <code class="code num">{{ text }}</code>
    <button class="btn" @click.prevent="copy">{{ done ? '✓' : t('detail.install') }}</button>
  </span>
</template>

<style scoped>
.wrap { display: inline-flex; align-items: stretch; border: 1px solid var(--line); border-radius: var(--radius-s); overflow: hidden; max-width: 100%; }
.code { padding: 6px 12px; background: var(--bg-raise); color: var(--cy); font-size: 13px; overflow: auto; white-space: nowrap; }
.btn { border: none; border-left: 1px solid var(--line); background: var(--panel-2); color: var(--fg-dim); padding: 0 14px; cursor: pointer; font-size: 13px; }
.btn:hover { color: var(--cy); }
</style>
