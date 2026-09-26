// data.ts — 数据访问层：大表 chunk 动态加载（进 /browse 才拉 ~350KB gzip）、
// 列数组解包、筛选（9574 行全量 computed 扫描 <5ms，无需索引结构）
import { ref } from 'vue'
import { meta } from '../data/meta'

export interface PluginRow {
  repo: string
  owner: string
  name: string
  verdict: string
  stars: number | null
  desc: string
  domain: string
  bundle: boolean
  pr: boolean
  hasEnrich: boolean
}

export interface EnrichInfo {
  pushedAt: string
  avatar: string
  lang: string
  license: string
  topics: string[]
}

const rows = ref<PluginRow[]>([])
const enrich = ref<Record<number, [string, string, string, string, string[]]>>({})
const loaded = ref(false)
let loading: Promise<void> | null = null

/** 拉取并解包大表 chunk（幂等；视图 onMounted 调用，ready 后渲染） */
export function ensureRows(): Promise<void> {
  if (loading) return loading
  loading = (async () => {
    const m = await import('../data/plugins')
    rows.value = m.ROWS.map((r) => {
      const repo = String(r[0])
      const slash = repo.indexOf('/')
      const stars = typeof r[3] === 'number' && r[3] >= 0 ? (r[3] as number) : null
      const flags = (r[6] as number) || 0
      return {
        repo,
        owner: repo.slice(0, slash),
        name: String(r[1]),
        verdict: String(r[2]),
        stars,
        desc: String(r[4]),
        domain: String(r[5]),
        bundle: (flags & 1) !== 0,
        pr: (flags & 2) !== 0,
        hasEnrich: (flags & 4) !== 0,
      }
    })
    enrich.value = m.ENRICH
    loaded.value = true
  })()
  return loading
}

export function useRows() {
  return { rows, loaded, ensureRows }
}

export function enrichAt(index: number): EnrichInfo | null {
  const e = enrich.value[index]
  return e ? { pushedAt: e[0], avatar: e[1], lang: e[2], license: e[3], topics: e[4] } : null
}

export function findRow(owner: string, name: string): PluginRow | null {
  const key = `${owner}/${name}`.toLowerCase()
  return rows.value.find((r) => r.repo.toLowerCase() === key) ?? null
}

export function rowIndex(row: PluginRow): number {
  return rows.value.indexOf(row)
}

export interface Filters {
  domain: string
  verdict: string
  stars: string
  q: string
}

export const STAR_BUCKETS: { key: string; min: number; max: number }[] = [
  { key: '500+', min: 500, max: Infinity },
  { key: '100-499', min: 100, max: 499 },
  { key: '50-99', min: 50, max: 99 },
  { key: '10-49', min: 10, max: 49 },
  { key: '1-9', min: 1, max: 9 },
  { key: '0', min: 0, max: 0 },
]

export function applyFilters(all: PluginRow[], f: Filters): PluginRow[] {
  const q = f.q.trim().toLowerCase()
  const bucket = STAR_BUCKETS.find((b) => b.key === f.stars)
  return all.filter((r) => {
    if (f.domain !== 'all' && r.domain !== f.domain) return false
    if (f.verdict !== 'all' && r.verdict !== f.verdict) return false
    if (bucket && (r.stars === null || r.stars < bucket.min || r.stars > bucket.max)) return false
    if (q && !(r.name.toLowerCase().includes(q) || r.repo.toLowerCase().includes(q)
      || r.desc.toLowerCase().includes(q))) return false
    return true
  })
}

export function byStars(a: PluginRow, b: PluginRow): number {
  return (b.stars ?? -1) - (a.stars ?? -1)
}

export { meta }
