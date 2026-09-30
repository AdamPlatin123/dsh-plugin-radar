<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { meta } from '../lib/data'

const { t } = useI18n()
interface Member { repo: string; name: string; verdict: string | null; desc: string }
interface Category { name: string; plugins: Member[] }
const categories: Category[] = meta.featured.categories ?? []
</script>

<template>
  <h1 class="page-h">{{ t('featured.title') }}</h1>
  <p class="sub">{{ t('featured.desc') }}</p>
  <section v-for="c in categories" :key="c.name" class="cat">
    <h2>{{ c.name }}<span class="n num">{{ c.plugins.length }}</span></h2>
    <div class="list">
      <router-link v-for="m in c.plugins" :key="m.repo" :to="`/plugin/${m.repo}`" class="item" :class="m.verdict ? `v-${m.verdict}` : ''">
        <span class="i-name">{{ m.name }}</span>
        <span class="i-desc">{{ m.desc }}</span>
      </router-link>
    </div>
  </section>
  <div v-if="!categories.length" class="empty">{{ t('empty.featuredNone') }}</div>
</template>

<style scoped>
.page-h { font-size: 22px; margin: 0 0 6px; }
.sub { color: var(--fg-dim); margin: 0 0 24px; }
.cat { margin-bottom: 26px; }
h2 { font-size: 17px; margin: 0 0 10px; }
.n { color: var(--fg-faint); font-size: 13px; margin-left: 8px; }
.list { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 8px; }
.item {
  display: flex; flex-direction: column; gap: 2px;
  border-left: 3px solid var(--tone, var(--line));
  background: var(--panel); border-radius: 0 var(--radius-s) var(--radius-s) 0;
  padding: 10px 14px; color: inherit;
}
.item:hover { text-decoration: none; background: var(--panel-2); }
.i-name { font-weight: 600; font-size: 14px; }
.i-desc { color: var(--fg-dim); font-size: 12.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty { padding: 60px 0; text-align: center; color: var(--fg-faint); }
</style>
