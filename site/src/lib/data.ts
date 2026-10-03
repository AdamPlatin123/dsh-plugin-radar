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
  dormant: boolean
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
        dormant: (flags & 8) !== 0,
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
  const key = canonicalRepo(`${owner}/${name}`).toLowerCase()
  return rows.value.find((r) => r.repo.toLowerCase() === key) ?? null
}

export function rowIndex(row: PluginRow): number {
  return rows.value.indexOf(row)
}

export { applyFilters, STAR_BUCKETS, type Filters } from './ranking'

export { byStars } from './ranking'

/** 策展条目（精选/整合包）的构建期状态：是否进入最终 rows + 真实判定/监测态 */
export interface CuratedStatus {
  indexed: boolean
  verdict: string | null
  dormant: boolean
  monitor: string | null   // 未收录时的监测档位：unlocated / gone / ambiguous / null（无记录）
}

export function curatedStatusOf(repo: string): CuratedStatus | null {
  const table = meta.curatedStatus as Record<string, CuratedStatus>
  return table[repo.toLowerCase()] ?? null
}

/** 策展条目源仓库地址（未收录条目的回退出口；已收录条目的详情页亦有同链接） */
export function sourceRepoUrl(repo: string): string {
  return `https://github.com/${canonicalRepo(repo)}`
}

export function canonicalRepo(repo: string): string {
  return (meta.repoAliases as Record<string, string>)[repo.toLowerCase()] ?? repo
}

export { meta }
