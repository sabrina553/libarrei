import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import type { MergedEdition } from '../lib/editions'
import { EditionsTable } from './EditionsTable'

const field = (value: unknown, conflict = false) => ({
  value, source: 'hardcover' as const, source_id: '1', conflict, alternatives: [],
  values: [{ value, source: 'hardcover' as const, source_id: '1' }],
})
// Two sources disagreeing, which is what the grid and the Issues count treat as a conflict.
const disputed = (a: unknown, b: unknown) => ({
  ...field(a, true),
  values: [{ value: a, source: 'hardcover' as const, source_id: '1' }, { value: b, source: 'goodreads' as const, source_id: '5' }],
})

const editions: MergedEdition[] = [
  { ids: { hardcover: ['1'], goodreads: ['5'] }, match_reason: null, confidence: 1, duplicates: [], duplicate_reasons: {}, slugs: {}, asin_checks: {}, quality: {}, fields: { isbn13: field('9780000000001'), pages: disputed(300, 310) } },
  { ids: { hardcover: ['2'], goodreads: ['3'], openlibrary: ['OL4M'] }, match_reason: 'isbn13', confidence: 1, duplicates: [], duplicate_reasons: {}, slugs: {}, asin_checks: {}, quality: {}, fields: { isbn13: field('9780000000002') } },
]

test('filters editions and opens one for detail', () => {
  render(<EditionsTable editions={editions} book="Test" />)
  expect(screen.getAllByRole('row')).toHaveLength(3)

  fireEvent.click(screen.getByText('Conflicts (1)'))
  expect(screen.getByText('9780000000001')).toBeInTheDocument()
  expect(screen.queryByText('9780000000002')).toBeNull()

  fireEvent.click(screen.getByText('9780000000001'))
  expect(screen.getByText('Pages')).toBeInTheDocument()
})

test('a header click sorts, a second reverses and a third restores the default', () => {
  render(<EditionsTable editions={editions} book="Test" />)
  const isbns = () => screen.getAllByText(/^97800000000\d\d$/).map((e) => e.textContent)
  const header = screen.getByRole('button', { name: 'ISBN-13' })

  fireEvent.click(header)
  expect(isbns()).toEqual(['9780000000001', '9780000000002'])
  expect(header).toHaveTextContent('ISBN-13 ▲')
  fireEvent.click(header)
  expect(isbns()).toEqual(['9780000000002', '9780000000001'])
  expect(header).toHaveTextContent('ISBN-13 ▼')
  fireEvent.click(header)
  expect(header).toHaveTextContent(/^ISBN-13$/)
})

test('sorting keeps the filter', () => {
  render(<EditionsTable editions={editions} book="Test" />)
  fireEvent.click(screen.getByText('Conflicts (1)'))
  fireEvent.click(screen.getByRole('button', { name: 'ISBN-13' }))
  expect(screen.queryByText('9780000000002')).toBeNull()
})

test('the issues cell shows a count with the breakdown on hover', () => {
  render(<EditionsTable editions={editions} book="Test" />)
  const cell = screen.getByTitle(/Conflicts: pages/)
  expect(cell).toHaveTextContent(/^\d+$/)
})
