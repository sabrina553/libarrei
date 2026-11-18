import { act, render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import { FieldGrid, type Resolved } from './FieldGrid'

const pages: Resolved = {
  value: 310,
  source: 'hardcover',
  source_id: '1',
  conflict: true,
  alternatives: [{ value: 320, source: 'openlibrary', source_id: 'OL1M' }],
  values: [
    { value: 310, source: 'hardcover', source_id: '1' },
    { value: 320, source: 'openlibrary', source_id: 'OL1M' },
  ],
}

test('shows each source value, marks the chosen one and the conflict', () => {
  render(<FieldGrid fields={{ pages }} order={['pages']} level="edition" />)

  expect(screen.getByText('310').closest('td')).toHaveClass('chosen')
  expect(screen.getByText('320').closest('td')).not.toHaveClass('chosen')
  expect(screen.getByText('conflict')).toBeInTheDocument()
  expect(screen.getAllByText('—')).toHaveLength(1)
})

test('shows every field and tells unsupported fields apart from empty ones', () => {
  render(<FieldGrid fields={{ pages }} order={['title', 'duration_seconds', 'pages']} level="edition" />)

  expect(screen.getByText('Title')).toBeInTheDocument()
  // Only Hardcover gives an audiobook length, so the other two cells are greyed out.
  const unsupported = screen.getAllByText('not provided')
  expect(unsupported).toHaveLength(2)
  expect(unsupported[0]).toHaveAttribute('title', 'Goodreads does not provide this field')
  // Empty: title on all three sources, duration on Hardcover, pages on Goodreads.
  expect(screen.getAllByText('—')).toHaveLength(5)
})

test('picking a value stages a correction for the source that disagrees', async () => {
  const { changeset } = await import('../lib/changeset')
  changeset.clear()
  render(<FieldGrid fields={{ pages }} order={['pages']} level="edition" staging={{ book: 'B', scope: 'ed', records: { hardcover: ['1'], openlibrary: ['OL1M'] } }} />)

  screen.getAllByText('Use this')[0].click()

  const [change] = changeset.all()
  expect(change.value).toBe(310)
  expect(change.corrections).toEqual([{ source: 'openlibrary', record: 'OL1M', current: 320 }])
})

test('labels values from duplicate records with a link to each record', () => {
  const isbn13: Resolved = {
    value: '9780000000001', source: 'openlibrary', source_id: 'OL1M', conflict: false, alternatives: [],
    values: [
      { value: '9780000000001', source: 'openlibrary', source_id: 'OL1M' },
      { value: '9780000000001', source: 'openlibrary', source_id: 'OL2M' },
      { value: '9780000000001', source: 'hardcover', source_id: '5' },
    ],
  }
  render(<FieldGrid fields={{ isbn13 }} order={['isbn13']} level="edition" />)

  expect(screen.getByText('OL1M')).toHaveAttribute('href', 'https://openlibrary.org/books/OL1M')
  expect(screen.getByText('OL2M')).toHaveAttribute('href', 'https://openlibrary.org/books/OL2M')
  // A single record needs no label.
  expect(screen.queryByText('5')).toBeNull()
})

test('flags a title holding the subtitle and stages the split parts', async () => {
  const { changeset } = await import('../lib/changeset')
  changeset.clear()
  const title: Resolved = {
    value: 'Dungeon Crawler Carl', source: 'goodreads', source_id: '9', conflict: true, alternatives: [],
    values: [
      { value: 'Dungeon Crawler Carl: A LitRPG Adventure', source: 'hardcover', source_id: '1' },
      { value: 'Dungeon Crawler Carl', source: 'goodreads', source_id: '9' },
    ],
  }
  render(<FieldGrid fields={{ title }} order={['title', 'subtitle']} level="edition"
    staging={{ book: 'B', scope: 'ed', records: { hardcover: ['1'], goodreads: ['9'] } }} />)

  expect(screen.getAllByText('subtitle may be in title')).toHaveLength(1)
  act(() => screen.getByText('Use “Dungeon Crawler Carl” as title').click())
  act(() => screen.getByText('Use “A LitRPG Adventure” as subtitle').click())

  const [titleChange, subtitleChange] = changeset.all()
  expect(titleChange).toMatchObject({ field: 'title', value: 'Dungeon Crawler Carl', chosenFrom: 'hardcover' })
  expect(titleChange.corrections).toEqual([{ source: 'hardcover', record: '1', current: 'Dungeon Crawler Carl: A LitRPG Adventure' }])
  expect(subtitleChange).toMatchObject({ field: 'subtitle', value: 'A LitRPG Adventure' })
  expect(subtitleChange.corrections).toEqual([
    { source: 'hardcover', record: '1', current: null },
    { source: 'goodreads', record: '9', current: null },
  ])
})

test('offers an edition statement split off a title as an edition statement', async () => {
  const { changeset } = await import('../lib/changeset')
  changeset.clear()
  const title: Resolved = {
    value: 'Dungeon Crawler Carl: Deluxe Edition', source: 'hardcover', source_id: '1', conflict: false, alternatives: [],
    values: [{ value: 'Dungeon Crawler Carl: Deluxe Edition', source: 'hardcover', source_id: '1' }],
  }
  render(<FieldGrid fields={{ title }} order={['title']} level="edition"
    staging={{ book: 'B', scope: 'ed', records: { hardcover: ['1'] } }} />)

  expect(screen.getByText('edition may be in title')).toBeInTheDocument()
  expect(screen.queryByText('Use “Deluxe Edition” as subtitle')).toBeNull()
  act(() => screen.getByText('Use “Deluxe Edition” as edition statement').click())
  expect(changeset.all()[0]).toMatchObject({ field: 'edition_statement', value: 'Deluxe Edition' })
})
