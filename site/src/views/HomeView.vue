<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { meta, useRows, curatedStatusOf, sourceRepoUrl } from '../lib/data'
import { dshStarLeaders } from '../lib/ranking'
import StatStrip from '../components/StatStrip.vue'
import PluginCard from '../components/PluginCard.vue'
import LazyOgImage from '../components/LazyOgImage.vue'
import VerdictBadge from '../components/VerdictBadge.vue'
import StarCount from '../components/StarCount.vue'

const { t } = useI18n()
const { rows, loaded, ensureRows } = useRows()
onMounted(ensureRows)

// 首页精选横滑：awesome-50 各分类头部成员（按 verdict 可用优先 + 名单序）
interface FeaturedCat { name: string; plugins: { repo: string; name: string; verdict: string | null; desc: string }[] }
const featured = computed(() => {
  const cats: FeaturedCat[] = meta.featured.categories ?? []
  const flat = cats.flatMap((c) => c.plugins.slice(0, 3).map((m) => ({ ...m, cat: c.name })))
  return flat.slice(0, 18)
})
// 未进入雷达索引的横滑条目：外链源仓库 + 监测态，而非 404 详情
const statusOf = curatedStatusOf
const monitorLabel = (repo: string) => {
  const monitor = statusOf(repo)?.monitor
  return monitor ? t('curated.recorded', { status: t(`stat.${monitor}`) }) : t('curated.noRecord')
}
const topByStars = computed(() => dshStarLeaders(rows.value))
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

  <section class="mt" v-if="featured.length">
    <h2>{{ t('featured.title') }}</h2>
    <div class="rail">
      <div v-for="f in featured" :key="f.repo" class="rail-card">
        <router-link v-if="statusOf(f.repo)?.indexed" :to="`/plugin/${f.repo}`" class="rail-link">
          <LazyOgImage :repo="f.repo" :name="f.name" :verdict="statusOf(f.repo)?.verdict || 'pending'" />
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

  <section class="mt">
    <h2>{{ t('nav.browse') }}<span class="h2sub num">{{ meta.totalBrowsable.toLocaleString() }}</span></h2>
    <div class="domain-grid">
      <router-link
        v-for="d in meta.domains" :key="d.slug"
        class="domain-tile" :to="`/browse?domain=${d.slug}`"
      >
        <span class="d-title">{{ d.title }}</span>
        <span class="d-count num">{{ (meta.counts as Record<string, number>)[d.slug] ?? 0 }}</span>
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
.mt { margin-top: 28px; }
h2 { font-size: 19px; margin: 0 0 14px; }
.h2sub { font-size: 13px; color: var(--fg-faint); margin-left: 8px; }

.rail { display: flex; gap: 12px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: thin; }
.rail-card { flex: 0 0 230px; border: 1px solid var(--line-soft); border-radius: var(--radius); overflow: hidden; background: var(--panel); }
.rail-link { display: block; color: inherit; }
.rail-link:hover { text-decoration: none; }
.rail-link.missing .rail-name { color: var(--fg-dim); }
.rail-link.missing .rail-desc { color: var(--fg-faint); }
.rail-body { padding: 8px 10px 10px; }
.rail-name { font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rail-desc { font-size: 12px; color: var(--fg-dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px; }

.domain-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 10px; }
.domain-tile {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 14px; background: var(--panel); border: 1px solid var(--line-soft);
  border-radius: var(--radius-s); color: var(--fg); font-size: 14px;
}
.domain-tile:hover { text-decoration: none; border-color: var(--cy); }
.d-count { color: var(--fg-faint); font-size: 13px; }

.top-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 14px; }
.ranking-note { margin: -6px 0 14px; color: var(--fg-dim); font-size: 13px; }

@media (max-width: 640px) {
  .hero { padding: 28px 18px; }
  h1 { font-size: 26px; }
}
</style>
