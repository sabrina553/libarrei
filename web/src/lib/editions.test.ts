import { expect, test } from 'vitest'
import { duplicateLabel, editionIssues, issueCount, issueSummary, editionKey, FILTERS, nextSort, sortEditions, type MergedEdition } from './editions'

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
  const conflicted = edition({ fields: { pages: { value: 1, source: 'hardcover', source_id: '2', conflict: true, alternatives: [],
    values: [{ value: 1, source: 'hardcover', source_id: '2' }, { value: 2, source: 'goodreads', source_id: '1' }] } } })
  expect(editionIssues(conflicted).conflicts).toEqual(['pages'])
  expect(FILTERS.conflicts.test(conflicted)).toBe(true)
  expect(FILTERS.issues.test(conflicted)).toBe(true)
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

const field = (value: unknown) => ({ value, source: 'hardcover' as const, source_id: '1', conflict: false, alternatives: [], values: [] })

test('default order: language, then best quality, then release date, gaps last', () => {
  const rows = [
    edition({ ids: { hardcover: ['none'] }, quality: { hardcover: 99 } }),
    edition({ ids: { hardcover: ['fr'] }, fields: { language: field('fr') }, quality: { hardcover: 90 } }),
    edition({ ids: { hardcover: ['en-later'] }, fields: { language: field('en'), release_date: field('2024') }, quality: { hardcover: 50 } }),
    edition({ ids: { hardcover: ['en-sparse'] }, fields: { language: field('en') }, quality: { hardcover: 20, goodreads: 30 } }),
    edition({ ids: { hardcover: ['en-earlier'] }, fields: { language: field('en'), release_date: field('2020') }, quality: { hardcover: 50 } }),
    edition({ ids: { hardcover: ['en-best'] }, fields: { language: field('en') }, quality: { hardcover: 10, goodreads: 95 } }),
  ]
  expect(sortEditions(rows, null).map((e) => e.ids.hardcover![0]))
    .toEqual(['en-best', 'en-earlier', 'en-later', 'en-sparse', 'fr', 'none'])
})

test('column sorts are numeric for numbers and keep gaps last both ways', () => {
  const rows = [
    edition({ ids: { hardcover: ['a'] }, quality: { hardcover: 9 } }),
    edition({ ids: { hardcover: ['b'] }, quality: { hardcover: 80 } }),
    edition({ ids: { hardcover: ['c'] } }),
  ]
  const order = (descending: boolean) => sortEditions(rows, { column: 'quality', descending }).map((e) => e.ids.hardcover![0])
  expect(order(false)).toEqual(['a', 'b', 'c'])
  expect(order(true)).toEqual(['b', 'a', 'c'])
  expect(nextSort(null, 'quality')).toEqual({ column: 'quality', descending: false })
  expect(nextSort({ column: 'quality', descending: false }, 'quality')).toEqual({ column: 'quality', descending: true })
  expect(nextSort({ column: 'quality', descending: true }, 'quality')).toBeNull()
})

test('issues count conflicts, missing fields and record flags, with a hover summary', () => {
  const v = (value: unknown, source: 'hardcover' | 'goodreads') => ({ value, source, source_id: source === 'hardcover' ? '2' : '1' })
  const e = edition({
    match_reason: 'fuzzy', confidence: 0.75, duplicates: ['goodreads'], duplicate_reasons: { goodreads: ['isbn13'] },
    fields: {
      pages: { value: 1, source: 'hardcover', source_id: '2', conflict: true, alternatives: [], values: [v(1, 'hardcover'), v(2, 'goodreads')] },
      publisher: { value: 'Ace', source: 'hardcover', source_id: '2', conflict: false, alternatives: [], values: [v('Ace', 'hardcover')] },
    },
  })
  const issues = editionIssues(e)
  expect(issues.conflicts).toEqual(['pages'])
  expect(issues.missing).toEqual(['publisher'])
  expect(issues.flags).toEqual(['duplicate · ISBN', 'fuzzy match (0.75)'])
  expect(issueCount(e)).toBe(4)
  expect(issueSummary(issues)).toBe('Conflicts: pages\nMissing: publisher\nduplicate · ISBN\nfuzzy match (0.75)')
  expect(issueCount(edition({}))).toBe(0)
})
