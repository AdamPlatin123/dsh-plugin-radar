<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { meta, useRows, curatedStatusOf, sourceRepoUrl, canonicalRepo } from '../lib/data'
import { dshStarLeaders, isDshProject } from '../lib/ranking'
import StatStrip from '../components/StatStrip.vue'
import PluginCard from '../components/PluginCard.vue'
import LazyOgImage from '../components/LazyOgImage.vue'
import VerdictBadge from '../components/VerdictBadge.vue'
import StarCount from '../components/StarCount.vue'

const { t } = useI18n()
const { rows, loaded, ensureRows } = useRows()
onMounted(ensureRows)
const topByStars = computed(() => dshStarLeaders(rows.value))
const browsableDsh = computed(() => rows.value.filter((r) => r.verdict === 'ok' && isDshProject(r)))
const domainCounts = computed(() => {
  const counts: Record<string, number> = {}
  for (const row of browsableDsh.value) counts[row.domain] = (counts[row.domain] ?? 0) + 1
  return counts
})

// 首页精选横滑：awesome-50 各分类头部成员（按 verdict 可用优先 + 名单序）
interface FeaturedCat { name: string; plugins: { repo: string; name: string; verdict: string | null; desc: string }[] }
const featured = computed(() => {
  const cats: FeaturedCat[] = meta.featured.categories ?? []
  const flat = cats.flatMap((c) => c.plugins.slice(0, 3).map((m) => ({ ...m, cat: c.name })))
  const seen = new Set(topByStars.value.map((m) => m.repo.toLowerCase()))
  return flat.filter((m) => {
    const repo = canonicalRepo(m.repo).toLowerCase()
    if (seen.has(repo)) return false
    seen.add(repo)
    return true
  }).slice(0, 18)
})
// 未进入雷达索引的横滑条目：外链源仓库 + 监测态，而非 404 详情
const statusOf = curatedStatusOf
const monitorLabel = (repo: string) => {
  const monitor = statusOf(repo)?.monitor
  return monitor ? t('curated.recorded', { status: t(`stat.${monitor}`) }) : t('curated.noRecord')
}
</script>

<template>
  <section class="hero">
    <div class="hero-inner">
      <h1>{{ t('hero.title') }}</h1>
      <p class="tagline">{{ t('hero.tagline') }}</p>
      <div class="cta">
        <router-link class="btn primary" to="/browse">{{ t('hero.cta') }}</router-link>
        <router-link class="btn ghost" to="/about">{{ t('hero.cta2') }}</router-link>
      </div>
    </div>
  </section>

  <StatStrip class="mt" />

  <section class="mt" v-if="loaded && featured.length">
    <h2>{{ t('featured.title') }}</h2>
    <div class="rail">
      <div v-for="f in featured" :key="f.repo" class="rail-card">
        <router-link v-if="statusOf(f.repo)?.indexed" :to="`/plugin/${f.repo}`" class="rail-link">
          <LazyOgImage :repo="canonicalRepo(f.repo)" :name="f.name" :verdict="statusOf(f.repo)?.verdict || 'pending'" />
          <div class="rail-body">
            <div class="rail-name">{{ f.name }}</div>
            <div class="rail-desc">{{ f.desc }}</div>
          </div>
        </router-link>
        <a v-else :href="sourceRepoUrl(f.repo)" target="_blank" rel="noopener" class="rail-link missing">
          <LazyOgImage :repo="f.repo" :name="f.name" :verdict="statusOf(f.repo)?.monitor || 'unlocated'" />
          <div class="rail-body">
            <div class="rail-name">{{ f.name }}</div>
            <div class="rail-desc">◌ {{ monitorLabel(f.repo) }} · ↗ {{ t('about.repo') }}</div>
          </div>
        </a>
      </div>
    </div>
  </section>

  <section class="mt" v-if="loaded">
    <h2>{{ t('nav.browse') }} · {{ t('filter.dshScope') }}<span class="h2sub num">{{ browsableDsh.length.toLocaleString() }}</span></h2>
    <div class="domain-grid">
      <router-link
        v-for="d in meta.domains" :key="d.slug"
        class="domain-tile" :to="`/browse?domain=${d.slug}`"
      >
        <span class="d-title">{{ d.title }}</span>
        <span class="d-count num">{{ domainCounts[d.slug] ?? 0 }}</span>
      </router-link>
    </div>
  </section>

  <section class="mt" v-if="loaded">
    <h2>★ {{ t('filter.sortStars') }}</h2>
    <p class="ranking-note">{{ t('filter.dshStarsNote') }}</p>
    <div class="top-grid">
      <PluginCard v-for="r in topByStars" :key="r.repo" :row="r" />
    </div>
  </section>
</template>

<style scoped>
.hero {
  border: 1px solid var(--line); border-radius: var(--radius);
  background:
    radial-gradient(600px 200px at 20% 0%, var(--cy-dim), transparent),
    var(--panel);
  padding: 44px 32px;
}
.hero-inner { max-width: 720px; }
h1 { margin: 0 0 10px; font-size: 34px; letter-spacing: 0.5px; }
.tagline { margin: 0 0 20px; color: var(--fg-dim); font-size: 16px; }
.cta { display: flex; gap: 12px; }
.btn { padding: 10px 22px; border-radius: var(--radius-s); font-size: 15px; }
.btn.primary { background: var(--cy); color: #04222b; font-weight: 600; }
.btn.primary:hover { text-decoration: none; filter: brightness(1.1); }
.btn.ghost { border: 1px solid var(--line); color: var(--fg-dim); }
.btn.ghost:hover { text-decoration: none; color: var(--cy); border-color: var(--cy); }
.mt { margin-top: 32px; min-width: 0; }
h2 { font-size: 19px; margin: 0 0 14px; overflow-wrap: anywhere; }
.h2sub { font-size: 13px; color: var(--fg-faint); margin-left: 8px; }

/* 整卡分列：列宽按可见张数均分轨道，横滑吸附，避免末张被裁成一条。 */
.rail {
  --rail-gap: 14px;
  --rail-visible: 4;
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: calc((100% - (var(--rail-visible) - 1) * var(--rail-gap)) / var(--rail-visible));
  gap: var(--rail-gap);
  min-width: 0;
  max-width: 100%;
  overflow-x: auto;
  overscroll-behavior-x: contain;
  scroll-snap-type: x mandatory;
  padding-bottom: 12px;
  scrollbar-width: thin;
  scrollbar-color: var(--line) transparent;
}
.rail::-webkit-scrollbar { height: 8px; }
.rail::-webkit-scrollbar-thumb { background: var(--line); border-radius: 99px; }
.rail-card {
  scroll-snap-align: start;
  min-width: 0;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--panel);
}
.rail-link { display: block; color: inherit; height: 100%; }
.rail-link:hover { text-decoration: none; }
.rail-link.missing .rail-name { color: var(--fg-dim); }
.rail-link.missing .rail-desc { color: var(--fg-faint); }
.rail-body { padding: 10px 12px 12px; }
.rail-name { font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rail-desc {
  font-size: 12px; color: var(--fg-dim); line-height: 1.45; margin-top: 4px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  min-height: 2.9em;
}

.domain-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 180px), 1fr));
  gap: 10px;
  min-width: 0;
}
.domain-tile {
  display: flex; justify-content: space-between; align-items: center; gap: 10px;
  padding: 12px 14px; background: var(--panel); border: 1px solid var(--line-soft);
  border-radius: var(--radius-s); color: var(--fg); font-size: 14px; min-width: 0;
}
.domain-tile:hover { text-decoration: none; border-color: var(--cy); }
.d-title { min-width: 0; line-height: 1.35; }
.d-count { color: var(--fg-faint); font-size: 13px; flex: none; }

.top-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr));
  gap: 18px;
  align-items: stretch;
  min-width: 0;
}
.top-grid :deep(.card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.top-grid :deep(.body) {
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 14px 16px 16px;
}
.top-grid :deep(.meta) { margin-top: auto; }
.ranking-note { margin: 0 0 16px; color: var(--fg-dim); font-size: 13px; max-width: 70ch; }

@media (max-width: 1080px) {
  .rail { --rail-visible: 3; }
}
@media (max-width: 760px) {
  .rail { --rail-visible: 2; }
}
@media (max-width: 560px) {
  .rail { --rail-visible: 1; }
  .hero { padding: 24px 16px; }
  h1 { font-size: 26px; }
  .tagline { font-size: 14px; }
  .cta { flex-wrap: wrap; }
  .btn { flex: 1 1 auto; text-align: center; }
  .h2sub { margin-left: 0; }
}
@media (max-width: 480px) {
  /* 两列时「Web UI 增强」会把最后一个字拆到下一行。 */
  .domain-grid { grid-template-columns: 1fr; }
}
</style>
