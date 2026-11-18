import { expect, test } from 'vitest'
import { inlineDiff, rowStates } from './cellStates'

const all = () => true

test('the most common value across sources wins, counted once per source', () => {
  const { states, modal } = rowStates('pages', [
    { value: 464, source: 'hardcover' },
    { value: 464, source: 'goodreads' },
    { value: 465, source: 'openlibrary' },
    { value: 465, source: 'openlibrary' },
  ], all)
  expect(modal).toBe('464')
  expect(states).toEqual({ hardcover: 'agrees', goodreads: 'agrees', openlibrary: 'differs', audible: 'missing' })
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
    .toEqual({ hardcover: 'missing', goodreads: 'agrees', openlibrary: 'missing', audible: 'missing' })
})

test('covers are not compared, since every source hosts its own copy', () => {
  const { states, problem } = rowStates('cover_url', [
    { value: 'a.jpg', source: 'hardcover' }, { value: 'b.jpg', source: 'goodreads' }, { value: 'c.jpg', source: 'openlibrary' },
    { value: 'd.jpg', source: 'audible' },
  ], all)
  expect(Object.values(states)).toEqual(['agrees', 'agrees', 'agrees', 'agrees'])
  expect(problem).toBe(false)
})

test('inline diff isolates the differing middle', () => {
  expect(inlineDiff('450', '468')).toEqual(['4', '50', ''])
  expect(inlineDiff('2020', '2025-12-30')).toEqual(['202', '0', ''])
  expect(inlineDiff('Ace Books', 'ace')).toEqual(['Ace', ' Books', ''])
})
