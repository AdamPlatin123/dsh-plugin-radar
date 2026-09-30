<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { meta } from '../lib/data'

const { t } = useI18n()
interface Member { repo: string; name: string; verdict: string | null; desc: string }
interface BundleForm { name: string; plugins: Member[] }
const bundles: BundleForm[] = meta.bundles.forms ?? []
</script>

<template>
  <h1 class="page-h">{{ t('bundles.title') }}</h1>
  <p class="sub">{{ t('bundles.desc') }}</p>
  <section v-for="b in bundles" :key="b.name" class="bundle">
    <h2>{{ b.name }}<span class="n num">{{ b.plugins.length }}</span></h2>
    <div class="list">
      <router-link v-for="m in b.plugins" :key="m.repo" :to="`/plugin/${m.repo}`" class="item">
        <span class="i-name">📦 {{ m.name }}</span>
        <span class="i-desc">{{ m.desc }}</span>
      </router-link>
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
.i-name { font-weight: 600; font-size: 14px; }
.i-desc { color: var(--fg-dim); font-size: 12.5px; }
.empty { padding: 60px 0; text-align: center; color: var(--fg-faint); }
</style>
