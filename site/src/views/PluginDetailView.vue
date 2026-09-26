<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRows, enrichAt, findRow, rowIndex, meta } from '../lib/data'
import LazyOgImage from '../components/LazyOgImage.vue'
import VerdictBadge from '../components/VerdictBadge.vue'
import StarCount from '../components/StarCount.vue'
import CopyChip from '../components/CopyChip.vue'

const props = defineProps<{ owner: string; name: string }>()
const { t } = useI18n()
const { rows, loaded, ensureRows } = useRows()
onMounted(ensureRows)

const row = computed(() => findRow(props.owner, props.name))
const enrich = computed(() => (row.value ? enrichAt(rowIndex(row.value)) : null))
const domainTitle = computed(() =>
  meta.domains.find((d) => d.slug === row.value?.domain)?.title ?? '')
const installCmd = computed(() => `dsh plugin add ${props.owner}/${props.name}`)
const repoUrl = computed(() => `https://github.com/${props.owner}/${props.name}`)
const fmtDate = (iso: string) => (iso ? iso.slice(0, 10) : '—')
</script>

<template>
  <div v-if="!loaded" class="loading">…</div>
  <div v-else-if="!row" class="empty">
    <p>404 · {{ owner }}/{{ name }}</p>
    <router-link to="/browse">{{ t('nav.browse') }}</router-link>
  </div>
  <article v-else :class="`v-${row.verdict}`">
    <div class="head">
      <div class="og">
        <LazyOgImage :repo="row.repo" :name="row.name" :verdict="row.verdict" />
      </div>
      <div class="head-info">
        <h1>{{ row.name }}</h1>
        <div class="sub num">{{ row.repo }}</div>
        <div class="badges">
          <VerdictBadge :verdict="row.verdict" />
          <span v-if="row.bundle" class="chip">📦 {{ t('card.bundle') }}</span>
          <span v-if="row.pr" class="chip">{{ t('card.pr') }}</span>
          <router-link class="chip link" :to="`/browse?domain=${row.domain}`">{{ domainTitle }}</router-link>
        </div>
        <div class="metrics">
          <span class="metric"><StarCount :stars="row.stars" /></span>
          <span v-if="enrich?.pushedAt" class="metric">{{ t('detail.updated') }} <b class="num">{{ fmtDate(enrich.pushedAt) }}</b></span>
          <span v-if="enrich?.lang" class="metric">{{ t('detail.language') }} <b>{{ enrich.lang }}</b></span>
          <span v-if="enrich?.license" class="metric">{{ t('detail.license') }} <b>{{ enrich.license }}</b></span>
        </div>
        <p class="desc">{{ row.desc || '—' }}</p>
        <div class="actions">
          <CopyChip :text="installCmd" />
          <a class="btn" :href="repoUrl" target="_blank" rel="noopener">↗ {{ t('detail.openRepo') }}</a>
        </div>
      </div>
    </div>

    <div v-if="enrich?.topics?.length" class="topics">
      <span v-for="tp in enrich.topics" :key="tp" class="chip">#{{ tp }}</span>
    </div>

    <aside class="provenance">
      <h3>{{ t('detail.source') }}</h3>
      <ul>
        <li>{{ t('detail.snapshot') }}: <span class="num">{{ meta.runId }}</span></li>
        <li>dsh-radar/v1 · <span class="num">{{ meta.generatedAt }}</span></li>
        <li v-if="meta.runnerLatest">{{ t('stat.runner') }} <span class="num">{{ meta.runnerLatest }}</span></li>
      </ul>
      <p class="note">{{ t('detail.notCurated') }}</p>
    </aside>
  </article>
</template>

<style scoped>
article { --tone: var(--cy); }
.head { display: grid; grid-template-columns: 340px 1fr; gap: 22px; align-items: start; }
.og { border-radius: var(--radius); overflow: hidden; border: 1px solid var(--line-soft); }
h1 { margin: 0 0 4px; font-size: 26px; }
.sub { color: var(--fg-faint); font-size: 13px; margin-bottom: 10px; }
.badges { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.chip { font-size: 12px; padding: 2px 10px; border-radius: 999px; border: 1px solid var(--line); color: var(--fg-dim); }
.chip.link:hover { color: var(--cy); border-color: var(--cy); text-decoration: none; }
.metrics { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 12px; color: var(--fg-dim); font-size: 13px; }
.metric b { color: var(--fg); font-weight: 600; }
.desc { color: var(--fg-dim); margin: 12px 0 16px; max-width: 640px; }
.actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.btn { border: 1px solid var(--line); border-radius: var(--radius-s); padding: 6px 14px; color: var(--fg-dim); font-size: 13px; }
.btn:hover { color: var(--cy); border-color: var(--cy); text-decoration: none; }
.topics { margin-top: 20px; display: flex; gap: 8px; flex-wrap: wrap; }
.provenance {
  margin-top: 26px; border: 1px dashed var(--line); border-radius: var(--radius);
  padding: 14px 18px; color: var(--fg-dim); font-size: 13px;
}
.provenance h3 { margin: 0 0 8px; font-size: 14px; color: var(--fg); }
.provenance ul { margin: 0; padding-left: 18px; }
.note { margin: 10px 0 0; color: var(--fg-faint); }
.loading, .empty { padding: 80px 0; text-align: center; color: var(--fg-faint); }

@media (max-width: 800px) {
  .head { grid-template-columns: 1fr; }
  .og { max-width: 420px; }
}
</style>
