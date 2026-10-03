<script setup lang="ts">
import { computed, onMounted, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { meta, useRows, applyFilters, byStars, type Filters } from '../lib/data'
import FilterBar from '../components/FilterBar.vue'
import VirtualCardGrid from '../components/VirtualCardGrid.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { rows, loaded, ensureRows } = useRows()
onMounted(ensureRows)

const filters = reactive<Filters>({
  scope: route.query.scope === 'all' ? 'all' : 'dsh',
  kind: ['plugin', 'bundle'].includes(String(route.query.kind)) ? String(route.query.kind) : 'all',
  domain: (route.query.domain as string) || 'all',
  // 默认展示 DSH 命名且运行级可用的项目；范围与判定可独立切换。
  verdict: (route.query.verdict as string) || 'ok',
  stars: (route.query.stars as string) || 'all',
  q: (route.query.q as string) || '',
})

// 筛选状态 ↔ URL query 双向同步（可分享、可后退）；默认值不写入 query
watch(filters, (f) => {
  const q: Record<string, string> = {}
  if (f.scope !== 'dsh') q.scope = f.scope
  if (f.kind !== 'all') q.kind = f.kind
  if (f.domain !== 'all') q.domain = f.domain
  if (f.verdict !== 'ok') q.verdict = f.verdict
  if (f.stars !== 'all') q.stars = f.stars
  if (f.q) q.q = f.q
  router.replace({ query: q })
})
watch(() => route.query, (q) => {
  filters.scope = q.scope === 'all' ? 'all' : 'dsh'
  filters.kind = ['plugin', 'bundle'].includes(String(q.kind)) ? String(q.kind) : 'all'
  filters.domain = (q.domain as string) || 'all'
  filters.verdict = (q.verdict as string) || 'ok'
  filters.stars = (q.stars as string) || 'all'
  filters.q = (q.q as string) || ''
})

const filtered = computed(() => {
  const out = applyFilters(rows.value, filters)
  return filters.q || filters.stars !== 'all' || filters.domain !== 'all' || filters.verdict !== 'all'
    ? [...out].sort(byStars)
    : out   // 无筛选时保持清单原序（域文件字典序 × 组内星序）
})
</script>

<template>
  <h1 class="page-h">{{ t('nav.browse') }}</h1>
  <p class="scope-note">{{ t('filter.scopeNote') }}</p>
  <FilterBar :model-value="filters" @update:model-value="Object.assign(filters, $event)" />
  <div class="count num">
    {{ t('filter.resultCount', { n: filtered.length.toLocaleString() }) }}
    <span class="scope">· {{ t('filter.defaultNote', { n: meta.totalIndexed.toLocaleString() }) }}</span>
  </div>
  <div v-if="!loaded" class="loading">…</div>
  <VirtualCardGrid v-else-if="filtered.length" :rows="filtered" />
  <div v-else class="empty">{{ t('empty.noResult') }}</div>
</template>

<style scoped>
.page-h { font-size: 22px; margin: 0 0 16px; }
.scope-note { color: var(--fg-dim); font-size: 13px; margin-bottom: 16px; }
.count { color: var(--fg-faint); font-size: 13px; margin-bottom: 10px; }
.scope { color: var(--fg-faint); }
.loading, .empty { padding: 60px 0; text-align: center; color: var(--fg-faint); }
</style>
