<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<template>
  <div class="about">
    <h1>{{ t('about.title') }}</h1>
    <p>{{ t('about.p1') }}</p>
    <p>{{ t('about.p2') }}</p>
    <p>{{ t('about.p3') }}</p>
    <ul class="links">
      <li>
        <a href="https://raw.githubusercontent.com/AdamPlatin123/dsh-plugin-radar/main/data/latest.json" target="_blank" rel="noopener">
          {{ t('about.api') }}
        </a>
        <code class="num">data/latest.json · data/plugins-all.json</code>
      </li>
      <li>
        <a href="https://github.com/AdamPlatin123/dsh-plugin-radar" target="_blank" rel="noopener">{{ t('about.repo') }}</a>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.about { max-width: 720px; }
h1 { font-size: 24px; margin: 0 0 14px; }
p { color: var(--fg-dim); line-height: 1.8; }
.links { margin-top: 18px; padding-left: 18px; color: var(--fg-dim); }
.links li { margin: 8px 0; }
.links code { margin-left: 10px; font-size: 12px; color: var(--fg-faint); }
</style>
