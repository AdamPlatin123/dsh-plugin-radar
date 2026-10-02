<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { meta, curatedStatusOf, sourceRepoUrl } from '../lib/data'

const { t } = useI18n()
interface Member { repo: string; name: string; verdict: string | null; desc: string }
interface BundleForm { name: string; plugins: Member[] }
const bundles: BundleForm[] = meta.bundles.forms ?? []

// 状态取构建期 curatedStatus（与最终 rows 对账）；未收录条目给监测态 + 源仓库回退
const statusOf = curatedStatusOf
const monitorLabel = (m: Member) => {
  const monitor = statusOf(m.repo)?.monitor
  return monitor ? t('curated.recorded', { status: t(`stat.${monitor}`) }) : t('curated.noRecord')
}
</script>

<template>
  <h1 class="page-h">{{ t('bundles.title') }}</h1>
  <p class="sub">{{ t('bundles.desc') }}</p>
  <section v-for="b in bundles" :key="b.name" class="bundle">
    <h2>{{ b.name }}<span class="n num">{{ b.plugins.length }}</span></h2>
    <div class="list">
      <template v-for="m in b.plugins" :key="m.repo">
        <router-link
          v-if="statusOf(m.repo)?.indexed"
          :to="`/plugin/${m.repo}`" class="item"
          :class="`v-${statusOf(m.repo)?.verdict ?? 'pending'}`"
        >
          <span class="i-name">📦 {{ m.name }}<span v-if="statusOf(m.repo)?.dormant" class="chip-d" :title="t('card.dormant')">😴</span></span>
          <span class="i-desc">{{ m.desc }}</span>
        </router-link>
        <!-- 未进入雷达索引的策展条目：呈现真实监测态 + 源仓库回退，不渲染 404 详情 -->
        <a v-else :href="sourceRepoUrl(m.repo)" target="_blank" rel="noopener" class="item missing v-unlocated">
          <span class="i-name">📦 {{ m.name }}</span>
          <span class="i-status">◌ {{ monitorLabel(m) }} · {{ t('curated.noRecord') }}</span>
          <span class="i-desc">{{ m.desc }}</span>
          <span class="i-src num">↗ github.com/{{ m.repo }}</span>
        </a>
      </template>
    </div>
  </section>
  <div v-if="!bundles.length" class="empty">{{ t('empty.featuredNone') }}</div>
</template>

<style scoped>
.page-h { font-size: 22px; margin: 0 0 6px; }
.sub { color: var(--fg-dim); margin: 0 0 24px; }
.bundle { margin-bottom: 26px; }
h2 { font-size: 17px; margin: 0 0 8px; }
.n { color: var(--fg-faint); font-size: 13px; margin-left: 8px; }
.b-desc { color: var(--fg-dim); font-size: 13.5px; margin: 0 0 10px; }
.list { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 8px; }
.item {
  display: flex; flex-direction: column; gap: 2px;
  background: var(--panel); border: 1px solid var(--line-soft); border-radius: var(--radius-s);
  padding: 10px 14px; color: inherit;
}
.item:hover { text-decoration: none; border-color: var(--cy); }
.missing { border-style: dashed; }
.missing .i-name { color: var(--fg-dim); }
.i-name { font-weight: 600; font-size: 14px; }
.i-desc { color: var(--fg-dim); font-size: 12.5px; }
.i-status { color: var(--fg-faint); font-size: 12px; }
.i-src { color: var(--cy); font-size: 12px; margin-top: 2px; }
.chip-d { margin-left: 6px; font-size: 12px; }
.empty { padding: 60px 0; text-align: center; color: var(--fg-faint); }
</style>
