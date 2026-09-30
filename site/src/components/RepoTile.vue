<script setup lang="ts">
import { computed } from 'vue'
import { tileColor, repoInitial, verdictColor } from '../lib/og'

// L2 兜底磁贴：纯前端确定性 SVG（仓库名 FNV 哈希取 12 色暗色板 + 首字母 + 判定色条）。
// 零网络零存储，OG 热链失败时永远在线（算法与 scripts/tile_assets.py 同源，见 ADR-0005）。
const props = defineProps<{ repo: string; name: string; verdict: string }>()
const bg = computed(() => tileColor(props.repo))
const initial = computed(() => repoInitial(props.name.replace(/^dsh[-_]?/i, '') || props.name))
const bar = computed(() => verdictColor(props.verdict))
</script>

<template>
  <svg class="tile" viewBox="0 0 320 160" preserveAspectRatio="xMidYMid slice" role="img" aria-hidden="true">
    <rect width="320" height="160" :fill="bg" />
    <rect width="320" height="160" fill="rgba(10,15,28,0.35)" />
    <text x="160" y="104" text-anchor="middle" class="glyph" :fill="'#e8f1fb'">{{ initial }}</text>
    <rect x="0" y="148" width="320" height="12" :fill="bar" opacity="0.9" />
    <text x="12" y="24" class="tag" fill="rgba(232,241,251,0.75)">{{ repo }}</text>
  </svg>
</template>

<style scoped>
.tile { width: 100%; height: 100%; display: block; }
.glyph { font: 700 72px var(--sans); }
.tag { font: 12px var(--mono); }
</style>
