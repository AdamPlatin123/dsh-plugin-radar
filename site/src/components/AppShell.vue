<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { toggleLang } from '../i18n'
import DataFreshnessChip from './DataFreshnessChip.vue'

const { t } = useI18n()
const route = useRoute()
const links = [
  { key: 'home', to: '/' },
  { key: 'browse', to: '/browse' },
  { key: 'featured', to: '/featured' },
  { key: 'bundles', to: '/bundles' },
  { key: 'about', to: '/about' },
]
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <div class="container bar-inner">
        <router-link to="/" class="brand">
          <span class="brand-dot"></span>
          <span class="brand-name">DSH <em>Radar</em></span>
        </router-link>
        <nav class="nav">
          <router-link
            v-for="l in links" :key="l.key" :to="l.to"
            class="nav-link" :class="{ active: route.path === l.to }"
          >{{ t(`nav.${l.key}`) }}</router-link>
        </nav>
        <div class="bar-right">
          <DataFreshnessChip />
          <button class="lang-btn" @click="toggleLang">{{ t('footer.lang') }}</button>
        </div>
      </div>
    </header>

    <main class="container main">
      <slot />
    </main>

    <footer class="footer">
      <div class="container foot-inner">
        <span>{{ t('footer.built') }}</span>
        <a href="https://github.com/AdamPlatin123/dsh-plugin-radar" target="_blank" rel="noopener">
          AdamPlatin123/dsh-plugin-radar
        </a>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.shell { min-height: 100vh; display: flex; flex-direction: column; max-width: 100%; }
.topbar {
  position: sticky; top: 0; z-index: 50;
  background: rgba(10, 15, 28, 0.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--line);
  min-width: 0;
}
.bar-inner { display: flex; align-items: center; gap: 20px; min-height: 56px; min-width: 0; }
.brand { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 16px; color: var(--fg); flex: none; }
.brand:hover { text-decoration: none; }
.brand-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--cy); box-shadow: 0 0 12px var(--cy); flex: none; }
.brand-name em { font-style: normal; color: var(--cy); }
.nav {
  display: flex; gap: 4px; flex: 1 1 auto; min-width: 0;
  overflow-x: auto; scrollbar-width: none;
}
.nav::-webkit-scrollbar { display: none; }
.nav-link {
  padding: 6px 12px; border-radius: var(--radius-s);
  color: var(--fg-dim); font-size: 14px; white-space: nowrap; flex: none;
}
.nav-link:hover { color: var(--fg); text-decoration: none; background: var(--bg-raise); }
.nav-link.active { color: var(--cy); background: var(--cy-dim); }
.bar-right { display: flex; align-items: center; gap: 10px; flex: none; }
.lang-btn {
  background: none; border: 1px solid var(--line); border-radius: var(--radius-s);
  padding: 4px 10px; font-size: 12px; color: var(--fg-dim); cursor: pointer;
}
.lang-btn:hover { color: var(--cy); border-color: var(--cy); }
.main { flex: 1 1 auto; min-width: 0; width: 100%; padding-top: 28px; padding-bottom: 48px; }
.footer { border-top: 1px solid var(--line-soft); padding: 18px 0; color: var(--fg-faint); font-size: 13px; }
.foot-inner { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }

@media (max-width: 860px) {
  .bar-inner { gap: 8px 12px; flex-wrap: wrap; padding: 8px 0 6px; }
  .brand { margin-right: auto; font-size: 15px; }
  .nav {
    order: 3;
    flex: 1 1 100%;
    overflow: visible;
    flex-wrap: wrap;
    gap: 2px;
  }
  .nav-link { padding: 5px 8px; }
}
</style>
