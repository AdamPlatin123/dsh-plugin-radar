<script setup lang="ts">
defineProps<{ stars: number | null }>()
</script>

<template>
  <span class="stars num" :title="stars === null ? '—' : String(stars)">
    <svg viewBox="0 0 16 16" class="star-ic" aria-hidden="true">
      <path d="M8 1.5l1.9 4 4.4.5-3.2 3 .9 4.3L8 11.1l-4 2.2.9-4.3-3.2-3 4.4-.5z" />
    </svg>
    <template v-if="stars === null">—</template>
    <template v-else>{{ stars >= 10000 ? (stars / 1000).toFixed(1) + 'k' : stars }}</template>
  </span>
</template>

<style scoped>
.stars { display: inline-flex; align-items: center; gap: 4px; color: var(--warn); font-size: 13px; }
.star-ic { width: 13px; height: 13px; fill: var(--warn); }
</style>
