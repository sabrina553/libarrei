import { expect, test } from 'vitest'
import { inlineDiff, missingColumns, rowStates } from './cellStates'

const all = () => true

test('the most common value across sources wins, counted once per source', () => {
  const { states, modal } = rowStates('pages', [
    { value: 464, source: 'hardcover' },
    { value: 464, source: 'goodreads' },
    { value: 465, source: 'openlibrary' },
    { value: 465, source: 'openlibrary' },
  ], all)
  expect(modal).toBe('464')
  expect(states).toEqual({ hardcover: 'agrees', goodreads: 'agrees', openlibrary: 'differs', amazon: 'missing' })
})

test('duplicate records that disagree among themselves differ', () => {
  const { states } = rowStates('pages', [
    { value: 464, source: 'hardcover' },
    { value: 464, source: 'openlibrary' },
    { value: 465, source: 'openlibrary' },
  ], all)
  expect(states.openlibrary).toBe('differs')
})

test('a gap only counts as missing when another source has a value', () => {
  expect(rowStates('asin', [], all).states.hardcover).toBe('empty')
  expect(rowStates('asin', [{ value: 'B0X', source: 'goodreads' }], all).states)
    .toEqual({ hardcover: 'missing', goodreads: 'agrees', openlibrary: 'missing', amazon: 'missing' })
})

test('covers are not compared, since every source hosts its own copy', () => {
  const { states, problem } = rowStates('cover_url', [
    { value: 'a.jpg', source: 'hardcover' }, { value: 'b.jpg', source: 'goodreads' }, { value: 'c.jpg', source: 'openlibrary' },
    { value: 'd.jpg', source: 'audible' }, { value: 'e.jpg', source: 'amazon' },
  ], all)
  expect(Object.values(states)).toEqual(['agrees', 'agrees', 'agrees', 'agrees'])
  expect(problem).toBe(false)
})

test('inline diff isolates the differing middle', () => {
  expect(inlineDiff('450', '468')).toEqual(['4', '50', ''])
  expect(inlineDiff('2020', '2025-12-30')).toEqual(['202', '0', ''])
  expect(inlineDiff('Ace Books', 'ace')).toEqual(['Ace', ' Books', ''])
})

test('amazon and audible share one column and count once', () => {
  const { states, modal } = rowStates('title', [
    { value: 'The Hobbit', source: 'hardcover' },
    { value: 'Hobbit', source: 'audible' },
    { value: 'Hobbit', source: 'amazon' },
    { value: 'The Hobbit', source: 'goodreads' },
  ], all)
  expect(modal).toBe('the hobbit')
  expect(states.amazon).toBe('differs')
  expect(Object.keys(states)).toEqual(['hardcover', 'goodreads', 'openlibrary', 'amazon'])
})

test('a source with no record is norecord, not missing, and raises no problem', () => {
  const { states, problem } = rowStates('pages', [
    { value: 464, source: 'hardcover' },
    { value: 464, source: 'goodreads' },
  ], all, (c) => c !== 'amazon' && c !== 'openlibrary')
  expect(states).toEqual({ hardcover: 'agrees', goodreads: 'agrees', openlibrary: 'norecord', amazon: 'norecord' })
  expect(problem).toBe(false)
})

test('missing columns lists only real gaps', () => {
  const { states } = rowStates('pages', [{ value: 1, source: 'hardcover' }], all, (c) => c !== 'amazon')
  expect(missingColumns(states)).toEqual(['goodreads', 'openlibrary'])
})
