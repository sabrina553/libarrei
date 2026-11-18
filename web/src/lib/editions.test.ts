import { expect, test } from 'vitest'
import { conflictCount, duplicateLabel, editionKey, FILTERS, type MergedEdition } from './editions'

const edition = (over: Partial<MergedEdition>): MergedEdition => ({
  ids: { hardcover: ['2'], goodreads: ['1'] },
  match_reason: 'isbn13',
  confidence: 1,
  asin_checks: {},
  quality: {},
  duplicates: [],
  duplicate_reasons: {},
  slugs: {},
  fields: {},
  ...over,
})

test('filters pick out the editions librarians need to look at', () => {
  const conflicted = edition({ fields: { pages: { value: 1, source: 'hardcover', source_id: '2', conflict: true, alternatives: [], values: [] } } })
  expect(conflictCount(conflicted)).toBe(1)
  expect(FILTERS.conflicts.test(conflicted)).toBe(true)
  expect(FILTERS.missing.test(edition({}))).toBe(true)
  expect(FILTERS.duplicates.test(edition({ duplicates: ['openlibrary'] }))).toBe(true)
  expect(FILTERS.fuzzy.test(edition({ match_reason: 'fuzzy' }))).toBe(true)
})

test('duplicate badges say which identifier the records share', () => {
  expect(duplicateLabel(edition({}))).toBeNull()
  expect(duplicateLabel(edition({ duplicates: ['openlibrary'], duplicate_reasons: { openlibrary: [] } }))).toBe('duplicate')
  expect(duplicateLabel(edition({ duplicates: ['openlibrary'], duplicate_reasons: { openlibrary: ['asin'] } }))).toBe('duplicate · ASIN')
  const both = edition({ duplicates: ['openlibrary', 'goodreads'], duplicate_reasons: { openlibrary: ['isbn10'], goodreads: ['isbn13', 'asin'] } })
  expect(duplicateLabel(both)).toBe('duplicate · ISBN · ASIN')
  expect(FILTERS.duplicateAsin.test(both)).toBe(true)
  expect(FILTERS.duplicateAsin.test(edition({ duplicates: ['goodreads'], duplicate_reasons: { goodreads: ['isbn13'] } }))).toBe(false)
})

test('edition keys ignore source order', () => {
  expect(editionKey(edition({ ids: { hardcover: ['2'], goodreads: ['1'] } })))
    .toBe(editionKey(edition({ ids: { goodreads: ['1'], hardcover: ['2'] } })))
})
