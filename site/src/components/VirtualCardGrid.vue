<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import type { PluginRow } from '../lib/data'
import PluginCard from './PluginCard.vue'

// 轻量自研虚拟网格：容器宽 → 列数 → 固定行高（卡片高度 + gap），
// 只渲染可视窗口 ±2 行（DOM 常驻约 40 卡）。9574 条滚动如常。
const props = defineProps<{ rows: PluginRow[] }>()

const CARD_W = 280
const CARD_H = 232
const GAP = 14
const PAD = 4

const wrap = ref<HTMLElement | null>(null)
const cols = ref(4)
const height = ref(600)
const scrollTop = ref(0)

function measure() {
  if (!wrap.value) return
  const w = wrap.value.clientWidth
  cols.value = Math.max(1, Math.floor((w + GAP) / (CARD_W + GAP)))
  height.value = wrap.value.clientHeight
}
let ro: ResizeObserver | undefined
onMounted(() => {
  measure()
  ro = new ResizeObserver(measure)
  if (wrap.value) ro.observe(wrap.value)
})
onUnmounted(() => ro?.disconnect())

const rowCount = computed(() => Math.ceil(props.rows.length / cols.value))
const totalH = computed(() => rowCount.value * (CARD_H + GAP) + PAD * 2)
const first = computed(() =>
  Math.max(0, Math.floor(scrollTop.value / (CARD_H + GAP)) - 2))
const visibleRows = computed(() => {
  const n = Math.ceil(height.value / (CARD_H + GAP)) + 4
  const out: { row: PluginRow; style: Record<string, string> }[] = []
  for (let r = first.value; r < Math.min(rowCount.value, first.value + n); r++) {
    for (let c = 0; c < cols.value; c++) {
      const idx = r * cols.value + c
      const item = props.rows[idx]
      if (!item) break
      out.push({
        row: item,
        style: {
          position: 'absolute',
          width: `${CARD_W}px`,
          height: `${CARD_H}px`,
          left: `${PAD + c * (CARD_W + GAP)}px`,
          top: `${PAD + r * (CARD_H + GAP)}px`,
        },
      })
    }
  }
  return out
})

// 筛选结果变化回到顶部
watch(() => props.rows, () => { scrollTop.value = 0 })
</script>

<template>
  <div ref="wrap" class="vwrap" @scroll.passive="scrollTop = ($event.target as HTMLElement).scrollTop">
    <div class="canvas" :style="{ height: `${totalH}px`, position: 'relative' }">
      <div v-for="it in visibleRows" :key="it.row.repo" :style="it.style">
        <PluginCard :row="it.row" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.vwrap {
  height: calc(100vh - 200px); min-height: 420px;
  overflow-y: auto; position: relative;
  scrollbar-width: thin; scrollbar-color: var(--line) transparent;
}
</style>
