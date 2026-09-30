// og.ts — 三层预览图的 L1（OG 热链）与 L2（确定性磁贴）工具
import { meta } from '../data/meta'

/** L1：GitHub OpenGraph 内容卡热链——免 API、按仓库内容自动生成；
 *  版本串用 snapshot_run_id（每数据轮自然换缓存）。 */
export function ogImageUrl(repo: string): string {
  return `https://opengraph.githubassets.com/${meta.runId || '1'}/${repo}`
}

// L2 磁贴：FNV-1a 哈希 → 12 色暗色板（与 scripts/tile_assets.py 的确定性语义同源，文档化于 ADR-0005）
const PALETTE = [
  '#155e75', '#166534', '#713f12', '#7c2d12', '#581c87', '#1e3a8a',
  '#0e7490', '#4d7c0f', '#9a3412', '#6d28d9', '#1d4ed8', '#0f766e',
]

export function fnv1a(s: string): number {
  let h = 0x811c9dc5
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h >>> 0
}

export function tileColor(repo: string): string {
  return PALETTE[fnv1a(repo) % PALETTE.length]
}

export function repoInitial(name: string): string {
  const c = name.trim().charAt(0).toUpperCase()
  return /[A-Z0-9]/.test(c) ? c : '?'
}

/** 判定 → 磁贴判定条颜色（与 tokens.css 四态一致） */
export function verdictColor(verdict: string): string {
  switch (verdict) {
    case 'ok': return 'var(--ok)'
    case 'incompatible': return 'var(--bad)'
    case 'pending': return 'var(--warn)'
    default: return 'var(--skip)'
  }
}
