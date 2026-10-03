interface StarRow {
  repo: string
  stars: number | null
}

export function byStars(a: StarRow, b: StarRow): number {
  return (b.stars ?? -1) - (a.stars ?? -1)
}

/** 首页榜单仅按仓库名中的独立 DSH / DeepSeek Harness 标识选取，不匹配作者或描述。 */
export function dshStarLeaders<T extends StarRow>(rows: readonly T[]): T[] {
  return rows.filter((row) => {
    const name = row.repo.slice(row.repo.lastIndexOf('/') + 1)
    return /(?:^|[-_.])(?:dsh|deepseek[-_.]harness)(?:$|[-_.])/i.test(name)
  }).sort(byStars).slice(0, 12)
}
