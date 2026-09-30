import { createI18n } from 'vue-i18n'
import { zh } from './zh'
import { en } from './en'

// 中文缺省、英文可切；选择持久化 localStorage
const stored = localStorage.getItem('radar-lang')
export const i18n = createI18n({
  legacy: false,
  locale: stored === 'en' ? 'en' : 'zh',
  fallbackLocale: 'zh',
  messages: { zh, en },
})

export function toggleLang() {
  const next = i18n.global.locale.value === 'zh' ? 'en' : 'zh'
  i18n.global.locale.value = next
  localStorage.setItem('radar-lang', next)
  document.documentElement.lang = next === 'zh' ? 'zh-CN' : 'en'
}
