interface StarRow {
  repo: string
  stars: number | null
}

export function byStars(a: StarRow, b: StarRow): number {
  return (b.stars ?? -1) - (a.stars ?? -1)
}

/** 命名范围筛选，不代表已核实关联；不匹配作者名或泛用工具描述。 */
export function isDshProject(row: StarRow): boolean {
  const name = row.repo.slice(row.repo.lastIndexOf('/') + 1)
  return /(?:^|[-_.])(?:dsh|deepseek[-_.]harness)(?:$|[-_.])/i.test(name)
}

export function dshStarLeaders<T extends StarRow>(rows: readonly T[]): T[] {
  return rows.filter(isDshProject).sort(byStars).slice(0, 12)
}

interface FilterRow extends StarRow {
  name: string
  verdict: string
  desc: string
  domain: string
  bundle: boolean
}

export interface Filters {
  scope: string
  kind: string
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

export function applyFilters<T extends FilterRow>(all: T[], f: Filters): T[] {
  const q = f.q.trim().toLowerCase()
  const bucket = STAR_BUCKETS.find((b) => b.key === f.stars)
  return all.filter((r) => {
    if (f.scope === 'dsh' && !isDshProject(r)) return false
    if (f.kind === 'plugin' && r.bundle) return false
    if (f.kind === 'bundle' && !r.bundle) return false
    if (f.domain !== 'all' && r.domain !== f.domain) return false
    if (f.verdict !== 'all' && r.verdict !== f.verdict) return false
    if (bucket && (r.stars === null || r.stars < bucket.min || r.stars > bucket.max)) return false
    if (q && !(r.name.toLowerCase().includes(q) || r.repo.toLowerCase().includes(q)
      || r.desc.toLowerCase().includes(q))) return false
    return true
  })
}
