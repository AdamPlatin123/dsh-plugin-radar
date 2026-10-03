import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

// 执行生产 TypeScript 模块，兼容 CI 的 Node 20，无额外测试依赖。
const source = await readFile(new URL('../src/lib/ranking.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 },
})
const { dshStarLeaders, byStars } = await import(
  `data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`
)

test('keeps DSH desktop, sidebar and TUI across verdicts; excludes popular general tools', () => {
  const rows = [
    { repo: 'mem0ai/mem0', stars: 66432, verdict: 'ok' },
    { repo: 'anywhere-labs/dsh-desktop', stars: 29748, verdict: 'incompatible' },
    { repo: 'omdsh-dev/DSH-better-sidebar', stars: 3942, verdict: 'pending' },
    { repo: 'ccch1mneyyy/dsh-TUI', stars: 3908, verdict: 'incompatible' },
    { repo: 'hairyf/deepseek-harness-desktop', stars: 2927, verdict: 'ok' },
  ]
  const original = [...rows]
  assert.deepEqual(dshStarLeaders(rows).map((row) => row.repo), rows.slice(1).map((row) => row.repo))
  assert.deepEqual(rows, original)
})

test('matches repository name tokens, not owners, descriptions or similar substrings', () => {
  const rows = [
    { repo: 'dsh-tools/general-agent', stars: 90000, desc: 'Supports DSH' },
    { repo: 'a/badsh-tool', stars: 80000 },
    { repo: 'a/dshark', stars: 70000 },
    { repo: 'a/deepseek-harnessed', stars: 60000 },
    { repo: 'a/oh-dsh', stars: 10 },
    { repo: 'a/DSH_tools', stars: 9 },
    { repo: 'a/deepseek.harness.desktop', stars: 8 },
  ]
  assert.deepEqual(dshStarLeaders(rows).map((row) => row.repo), rows.slice(4).map((row) => row.repo))
})

test('filters before taking the top 12 and sorts unknown stars last', () => {
  const unrelated = Array.from({ length: 20 }, (_, i) => ({ repo: `a/general-${i}`, stars: 100000 }))
  const related = Array.from({ length: 13 }, (_, i) => ({ repo: `a/dsh-${i}`, stars: i }))
  const rows = [...unrelated, ...related, { repo: 'a/dsh-unknown', stars: null }]
  assert.deepEqual(dshStarLeaders(rows).map((row) => row.stars), [12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1])
  assert.deepEqual(dshStarLeaders(related.slice(0, 1).concat(rows.slice(-1))).map((row) => row.stars), [0, null])
  assert.deepEqual(dshStarLeaders([]), [])
  assert.equal(byStars({ repo: 'a/one', stars: null }, { repo: 'b/two', stars: null }), 0)
})
