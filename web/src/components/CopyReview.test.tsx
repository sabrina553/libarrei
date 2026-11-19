import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, test } from 'vitest'
import { changeset } from '../lib/changeset'
import type { MergedEdition } from '../lib/editions'
import { merges, mergesToMarkdown } from '../lib/merges'
import { EditionsTable } from './EditionsTable'

const f = (value: unknown, source_id: string) => ({
  value, source: 'hardcover' as const, source_id, conflict: false, alternatives: [],
  values: [{ value, source: 'hardcover' as const, source_id }],
})
const base = { match_reason: null, confidence: 1, duplicates: [], duplicate_reasons: {}, format_clash_isbns: [],
  asin_stores: {}, asin_checks: {}, quality: {}, slugs: {} }
const best: MergedEdition = { ...base, ids: { hardcover: ['30407789'] }, fields: {
  isbn13: f('9781405989411', '30407789'), title: f('Dungeon Crawler Carl', '30407789'), pages: f(446, '30407789'),
  publisher: f('Dandy House', '30407789') } }
const copy: MergedEdition = { ...base, ids: { hardcover: ['33335690'] }, stub_of: { hardcover: ['30407789'] }, fields: {
  title: f('Dungeon Crawler Carl', '33335690'), pages: f(447, '33335690'), publisher: f('Dandy House', '33335690') } }

beforeEach(() => { merges.clear(); changeset.clear() })

test('a possible duplicate can have a value kept, then be merged into the best version', () => {
  render(<EditionsTable editions={[best, copy]} book="Dungeon Crawler Carl" />)
  expect(screen.queryByText('33335690')).toBeNull()
  fireEvent.click(screen.getByText('+1 possible duplicate'))
  expect(screen.getByText(/matches on title, publisher/)).toBeInTheDocument()

  fireEvent.click(screen.getByText('Keep this value'))
  expect(changeset.all()[0]).toMatchObject({ field: 'pages', value: 447, chosenFrom: 'hardcover' })
  fireEvent.click(screen.getByText('Merge into this version'))

  expect(merges.all().merges).toEqual([expect.objectContaining({
    record: '33335690', into: { source: 'hardcover', record: '30407789' }, carried: ['pages'] })])
  expect(screen.getByText(/1 merged/)).toBeInTheDocument()
  expect(screen.queryByText('+1 possible duplicate')).toBeNull()
  expect(mergesToMarkdown(merges.all().merges)).toContain('merge hardcover `33335690` into hardcover `30407789`; keep its pages')
})

test('dismissing a possible duplicate lists it as an ordinary edition', () => {
  render(<EditionsTable editions={[best, copy]} book="Dungeon Crawler Carl" />)
  fireEvent.click(screen.getByText('+1 possible duplicate'))
  fireEvent.click(screen.getByText('Not a duplicate'))
  expect(merges.all().notDuplicates).toEqual(['hardcover:33335690'])
  expect(screen.queryByText(/possible duplicate/)).toBeNull()
  expect(screen.getAllByRole('row')).toHaveLength(3)
})

test('the review compares fields in-line and marks the match keys', () => {
  render(<EditionsTable editions={[best, copy]} book="Dungeon Crawler Carl" />)
  fireEvent.click(screen.getByText('+1 possible duplicate'))
  const pages = screen.getByRole('rowheader', { name: 'Pages' }).closest('tr')!
  expect(pages).toHaveClass('differs')
  const publisher = screen.getByRole('rowheader', { name: /Publisher/ }).closest('tr')!
  expect(publisher).toHaveClass('same')
  expect(publisher).toHaveTextContent('match key')
})

test('several editions can be open at once', () => {
  const other = { ...best, ids: { hardcover: ['1'] }, fields: { isbn13: f('9780000000009', '1') } }
  render(<EditionsTable editions={[best, other]} book="Dungeon Crawler Carl" />)
  fireEvent.click(screen.getByText('9781405989411'))
  fireEvent.click(screen.getByText('9780000000009'))
  expect(screen.getAllByText(/Only problems/)).toHaveLength(2)
})
