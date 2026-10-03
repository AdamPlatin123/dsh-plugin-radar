import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/lib/pages-route.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 },
})
const { pagesFallbackRoute } = await import(
  `data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`
)

test('restores Pages 404 details and browse filters before history router initialization', () => {
  const base = '/dsh-plugin-radar/'
  assert.equal(pagesFallbackRoute(base, '#/plugin/hairyf/deepseek-harness-desktop?v=1#source', base),
    '/dsh-plugin-radar/plugin/hairyf/deepseek-harness-desktop?v=1#source')
  assert.equal(pagesFallbackRoute(base, '#/browse?verdict=all&q=dsh%20desktop', base),
    '/dsh-plugin-radar/browse?verdict=all&q=dsh%20desktop')
})

test('preserves normal anchors and already valid history routes', () => {
  const base = '/dsh-plugin-radar/'
  assert.equal(pagesFallbackRoute(base, '#community', base), null)
  assert.equal(pagesFallbackRoute(base, '', base), null)
  assert.equal(pagesFallbackRoute(`${base}plugin/a/b`, '#/source', base), null)
})
