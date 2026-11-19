import type { LanguagePrefs } from '../settings/languages'
import type { MergedEdition } from './editions'

export type LanguageView = {
  shown: MergedEdition[]
  hidden: number
  // Which rule picked the editions: the preferred languages, the fallback, or none at all.
  rule: 'off' | 'preferred' | 'fallback-all' | 'fallback-english' | 'fallback-none'
}

const languageOf = (e: MergedEdition) => {
  const value = e.fields.language?.value
  return typeof value === 'string' && value ? value.toLowerCase() : null
}

/**
 * Keeps editions in the preferred languages. Editions with no language recorded always stay,
 * since a gap in the data is not a reason to hide a record. When no edition is in a preferred
 * language, the fallback decides: everything, English only, or nothing.
 */
export function byLanguage(editions: MergedEdition[], prefs: LanguagePrefs): LanguageView {
  if (!prefs.preferred.length) return { shown: editions, hidden: 0, rule: 'off' }
  const wanted = new Set(prefs.preferred.map((c) => c.toLowerCase()))
  const keep = (codes: Set<string>) => editions.filter((e) => { const l = languageOf(e); return l === null || codes.has(l) })
  const view = (shown: MergedEdition[], rule: LanguageView['rule']) => ({ shown, hidden: editions.length - shown.length, rule })
  if (editions.some((e) => wanted.has(languageOf(e) ?? ''))) return view(keep(wanted), 'preferred')
  if (prefs.fallback === 'all') return view(editions, 'fallback-all')
  if (prefs.fallback === 'english') return view(keep(new Set(['en'])), 'fallback-english')
  return view(editions.filter((e) => languageOf(e) === null), 'fallback-none')
}

/** Sort rank: preferred languages first, in the order chosen, then the rest. */
export function languageRank(edition: MergedEdition, preferred: string[]): number {
  const i = preferred.map((c) => c.toLowerCase()).indexOf(languageOf(edition) ?? '')
  return i === -1 ? preferred.length : i
}
