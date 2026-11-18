import { expect, test } from 'vitest'
import { conflictCount, editionKey, FILTERS, type MergedEdition } from './editions'

const edition = (over: Partial<MergedEdition>): MergedEdition => ({
  ids: { hardcover: ['2'], goodreads: ['1'] },
  match_reason: 'isbn13',
  confidence: 1,
  duplicates: [],
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

test('edition keys ignore source order', () => {
  expect(editionKey(edition({ ids: { hardcover: ['2'], goodreads: ['1'] } })))
    .toBe(editionKey(edition({ ids: { goodreads: ['1'], hardcover: ['2'] } })))
})
