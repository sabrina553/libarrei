import { expect, test } from 'vitest'
import type { MergedEdition } from './editions'
import { byLanguage, languageRank } from './languages'

const edition = (language: string | null): MergedEdition => ({
  ids: { hardcover: [language ?? 'none'] }, match_reason: null, confidence: 1, asin_checks: {}, asin_stores: {}, quality: {},
  duplicates: [], duplicate_reasons: {}, format_clash_isbns: [], slugs: {},
  fields: language ? { language: { value: language, source: 'hardcover', source_id: '1', conflict: false, alternatives: [], values: [] } } : {},
})
const langs = (v: { shown: MergedEdition[] }) => v.shown.map((e) => e.fields.language?.value ?? null)
const mixed = [edition('en'), edition('es'), edition('ja'), edition(null)]

test('no preference shows everything', () => {
  expect(byLanguage(mixed, { preferred: [], fallback: 'none' })).toMatchObject({ hidden: 0, rule: 'off' })
})

test('preferred languages are kept, and editions without a language stay', () => {
  const view = byLanguage(mixed, { preferred: ['es', 'en'], fallback: 'none' })
  expect(langs(view)).toEqual(['en', 'es', null])
  expect(view).toMatchObject({ hidden: 1, rule: 'preferred' })
})

test('the fallback applies only when no edition is in a preferred language', () => {
  const noFrench = [edition('en'), edition('ja')]
  expect(langs(byLanguage(noFrench, { preferred: ['fr'], fallback: 'all' }))).toEqual(['en', 'ja'])
  expect(langs(byLanguage(noFrench, { preferred: ['fr'], fallback: 'english' }))).toEqual(['en'])
  expect(byLanguage(noFrench, { preferred: ['fr'], fallback: 'none' })).toMatchObject({ shown: [], hidden: 2, rule: 'fallback-none' })
})

test('preferred languages rank first, in the chosen order', () => {
  expect(languageRank(edition('es'), ['es', 'en'])).toBe(0)
  expect(languageRank(edition('en'), ['es', 'en'])).toBe(1)
  expect(languageRank(edition('ja'), ['es', 'en'])).toBe(2)
})
