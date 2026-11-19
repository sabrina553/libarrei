import { beforeEach, expect, test } from 'vitest'
import { buildChange, changeset, toMarkdown } from './changeset'

beforeEach(() => changeset.clear())

const values = [
  { value: 310, source: 'hardcover' as const, source_id: 'h1' },
  { value: 320, source: 'openlibrary' as const, source_id: 'OL1M' },
  { value: 310, source: 'goodreads' as const, source_id: 'g1' },
]
const records = { hardcover: ['h1'], openlibrary: ['OL1M', 'OL2M'], goodreads: ['g1'] }

test('a pick corrects only the records that disagree or lack the field', () => {
  const change = buildChange('The Hobbit', 'ed', 'pages', values[0], values, records)
  expect(change.corrections).toEqual([
    { source: 'openlibrary', record: 'OL1M', current: 320 },
    { source: 'openlibrary', record: 'OL2M', current: null },
  ])
})

test('restaging a field replaces the earlier pick, and markdown groups by source', () => {
  changeset.stage(buildChange('The Hobbit', 'ed', 'pages', values[0], values, records))
  changeset.stage(buildChange('The Hobbit', 'ed', 'pages', values[1], values, records))
  expect(changeset.all()).toHaveLength(1)
  const md = toMarkdown(changeset.all())
  expect(md).toContain('## hardcover')
  expect(md).toContain('record `h1`, pages: 310 → 320 (from openlibrary)')
})

test('never stages corrections against reference-only stores, but they can be picked', () => {
  const values = [
    { value: 300, source: 'hardcover' as const, source_id: '1' },
    { value: 310, source: 'amazon' as const, source_id: 'B1' },
    { value: 320, source: 'audible' as const, source_id: 'B2' },
  ]
  const records = { hardcover: ['1'], amazon: ['B1'], audible: ['B2'], goodreads: ['9'] }
  const fromHc = buildChange('B', 'ed', 'pages', values[0], values, records)
  expect(fromHc.corrections.map((c) => c.source)).toEqual(['goodreads'])
  const fromAmazon = buildChange('B', 'ed', 'pages', values[1], values, records)
  expect(fromAmazon.chosenFrom).toBe('amazon')
  expect(fromAmazon.corrections.map((c) => c.source)).toEqual(['hardcover', 'goodreads'])
})

test('picking no value only corrects records that hold one', () => {
  const values = [
    { value: 'Abridged', source: 'hardcover' as const, source_id: '1' },
    { value: 'Abridged', source: 'amazon' as const, source_id: 'B1' },
  ]
  const change = buildChange('B', 'ed', 'edition_statement', { value: null, source: 'goodreads', source_id: '9' },
    values, { hardcover: ['1'], goodreads: ['9'], openlibrary: ['OL1M'], amazon: ['B1'] })
  expect(change.value).toBeNull()
  expect(change.corrections).toEqual([{ source: 'hardcover', record: '1', current: 'Abridged' }])
})
