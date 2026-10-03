/** 将 Pages 404 回退产生的 #/ 路径恢复为历史路由，保留筛选参数和原始锚点。 */
export function pagesFallbackRoute(pathname: string, hash: string, base: string): string | null {
  return pathname === base && hash.startsWith('#/') ? base + hash.slice(2) : null
}
