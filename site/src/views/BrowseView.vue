<script setup lang="ts">
import { computed, onMounted, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useRows, applyFilters, byStars, type Filters } from '../lib/data'
import FilterBar from '../components/FilterBar.vue'
import VirtualCardGrid from '../components/VirtualCardGrid.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { rows, loaded, ensureRows } = useRows()
onMounted(ensureRows)

const filters = reactive<Filters>({
  domain: (route.query.domain as string) || 'all',
  verdict: (route.query.verdict as string) || 'all',
  stars: (route.query.stars as string) || 'all',
  q: (route.query.q as string) || '',
})

// 筛选状态 ↔ URL query 双向同步（可分享、可后退）
watch(filters, (f) => {
  const q: Record<string, string> = {}
  if (f.domain !== 'all') q.domain = f.domain
  if (f.verdict !== 'all') q.verdict = f.verdict
  if (f.stars !== 'all') q.stars = f.stars
  if (f.q) q.q = f.q
  router.replace({ query: q })
})
watch(() => route.query, (q) => {
  filters.domain = (q.domain as string) || 'all'
  filters.verdict = (q.verdict as string) || 'all'
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
  <FilterBar v-model="filters" />
  <div class="count num">{{ t('filter.resultCount', { n: filtered.length.toLocaleString() }) }}</div>
  <div v-if="!loaded" class="loading">…</div>
  <VirtualCardGrid v-else-if="filtered.length" :rows="filtered" />
  <div v-else class="empty">{{ t('empty.noResult') }}</div>
</template>

<style scoped>
.page-h { font-size: 22px; margin: 0 0 16px; }
.count { color: var(--fg-faint); font-size: 13px; margin-bottom: 10px; }
.loading, .empty { padding: 60px 0; text-align: center; color: var(--fg-faint); }
</style>
