<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { PluginRow } from '../lib/data'
import LazyOgImage from './LazyOgImage.vue'
import VerdictBadge from './VerdictBadge.vue'
import StarCount from './StarCount.vue'

const props = defineProps<{ row: PluginRow }>()
const { t } = useI18n()
</script>

<template>
  <router-link
    class="card"
    :class="`v-${row.verdict}`"
    :to="`/plugin/${row.repo}`"
  >
    <LazyOgImage :repo="row.repo" :name="row.name" :verdict="row.verdict" />
    <div class="body">
      <div class="title-row">
        <span class="name" :title="row.name">{{ row.name }}</span>
        <StarCount :stars="row.stars" />
      </div>
      <p class="desc" :title="row.desc">{{ row.desc || '—' }}</p>
      <div class="meta">
        <VerdictBadge :verdict="row.verdict" />
        <span v-if="row.bundle" class="chip bundle">📦 {{ t('card.bundle') }}</span>
        <span v-if="row.pr" class="chip pr">{{ t('card.pr') }}</span>
        <span class="owner">{{ row.owner }}</span>
      </div>
    </div>
  </router-link>
</template>

<style scoped>
.card {
  display: block; background: var(--panel); border: 1px solid var(--line-soft);
  border-radius: var(--radius); overflow: hidden;
  transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}
.card:hover {
  transform: translateY(-2px);
  border-color: var(--tone, var(--cy));
  box-shadow: var(--shadow);
  text-decoration: none;
}
.body { padding: 12px 14px 14px; }
.title-row { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.name { font-weight: 600; font-size: 15px; color: var(--fg); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.desc {
  margin: 6px 0 10px; color: var(--fg-dim); font-size: 13px; line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  min-height: 2.9em;
}
.meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.chip { font-size: 11px; padding: 1px 8px; border-radius: 999px; border: 1px solid var(--line); color: var(--fg-dim); }
.owner { margin-left: auto; font-size: 12px; color: var(--fg-faint); font-family: var(--mono); }
</style>
