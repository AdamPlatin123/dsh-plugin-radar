<script setup lang="ts">
import { ref } from 'vue'
import RepoTile from './RepoTile.vue'
import { ogImageUrl } from '../lib/og'

// 三层预览图的 L1→L2 切换：OG 卡懒加载热链，onerror 即换站内磁贴（不重试外链）。
const props = defineProps<{ repo: string; name: string; verdict: string }>()
const failed = ref(false)
const url = ogImageUrl(props.repo)
</script>

<template>
  <div class="ogwrap">
    <img
      v-if="!failed"
      :src="url"
      alt=""
      loading="lazy"
      referrerpolicy="no-referrer"
      decoding="async"
      class="ogimg"
      @error="failed = true"
    />
    <RepoTile v-else :repo="repo" :name="name" :verdict="verdict" />
  </div>
</template>

<style scoped>
.ogwrap { width: 100%; aspect-ratio: 2 / 1; overflow: hidden; background: var(--bg-raise); position: relative; }
.ogimg { width: 100%; height: 100%; object-fit: cover; display: block; }
</style>
