import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import type { MergedEdition } from '../lib/editions'
import { EditionsTable } from './EditionsTable'

const field = (value: unknown, conflict = false) => ({
  value, source: 'hardcover' as const, source_id: '1', conflict, alternatives: [],
  values: [{ value, source: 'hardcover' as const, source_id: '1' }],
})

const editions: MergedEdition[] = [
  { ids: { hardcover: ['1'] }, match_reason: null, confidence: 1, duplicates: [], fields: { isbn13: field('9780000000001'), pages: field(300, true) } },
  { ids: { hardcover: ['2'], goodreads: ['3'], openlibrary: ['OL4M'] }, match_reason: 'isbn13', confidence: 1, duplicates: [], fields: { isbn13: field('9780000000002') } },
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
