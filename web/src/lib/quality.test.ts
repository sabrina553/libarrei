import { expect, test } from 'vitest'
import { columnQuality, suggestion } from './cellStates'
import { FILTERS, isSparse, lowestQuality, stubLabel, type MergedEdition } from './editions'

const edition = (over: Partial<MergedEdition>): MergedEdition => ({
  ids: { hardcover: ['1'] }, match_reason: null, confidence: 1, asin_checks: {}, quality: {},
  duplicates: [], duplicate_reasons: {}, slugs: {}, fields: {}, ...over,
})

test('a much fuller record breaks a tie', () => {
  const values = [{ value: 'Ace', source: 'hardcover' as const }, { value: 'Penguin', source: 'goodreads' as const }]
  expect(suggestion('publisher', values, { hardcover: 90, goodreads: 30 })?.value).toBe('Ace')
  // A small gap says nothing.
  expect(suggestion('publisher', values, { hardcover: 70, goodreads: 50 })).toBeNull()
  expect(suggestion('publisher', values)).toBeNull()
})

test('quality never outvotes agreement', () => {
  const values = [
    { value: 'Ace', source: 'hardcover' as const },
    { value: 'Penguin', source: 'goodreads' as const },
    { value: 'Penguin', source: 'openlibrary' as const },
  ]
  expect(suggestion('publisher', values, { hardcover: 100, goodreads: 10, openlibrary: 10 })?.value).toBe('Penguin')
})

test('a shared column scores as its best source', () => {
  expect(columnQuality('amazon', { audible: 80, amazon: 40 })).toBe(80)
  expect(columnQuality('hardcover', {})).toBeUndefined()
})

test('sparse editions and their stub hint', () => {
  const full = edition({ ids: { hardcover: ['9'] }, quality: { hardcover: 100 },
    fields: { isbn13: { value: '9780593820247', source: 'hardcover', source_id: '9', conflict: false, alternatives: [], values: [] } } })
  const stub = edition({ ids: { hardcover: ['32478399'] }, quality: { hardcover: 31, goodreads: 90 }, stub_of: { hardcover: ['9'] } })
  expect(lowestQuality(stub)).toBe(31)
  expect(isSparse(stub) && FILTERS.sparse.test(stub)).toBe(true)
  expect(FILTERS.sparse.test(full)).toBe(false)
  expect(stubLabel(stub, [full, stub])).toBe('possible stub of 9780593820247')
  expect(stubLabel(full, [full, stub])).toBeNull()
})
