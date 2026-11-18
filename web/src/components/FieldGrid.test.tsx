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
  render(<FieldGrid fields={{ pages }} order={['title', 'asin', 'pages']} level="edition" />)

  expect(screen.getByText('Title')).toBeInTheDocument()
  // Only Goodreads can carry an ASIN, so the other two cells are greyed out.
  const unsupported = screen.getAllByText('not provided')
  expect(unsupported).toHaveLength(2)
  expect(unsupported[0]).toHaveAttribute('title', 'Hardcover does not provide this field')
  // Empty: title on all three sources, ASIN on Goodreads, pages on Goodreads.
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

test('flags a title holding the subtitle and stages the split parts', async () => {
  const { changeset } = await import('../lib/changeset')
  changeset.clear()
  const title: Resolved = {
    value: 'Dungeon Crawler Carl', source: 'goodreads', source_id: '9', conflict: true, alternatives: [],
    values: [
      { value: 'Dungeon Crawler Carl: Deluxe Edition', source: 'hardcover', source_id: '1' },
      { value: 'Dungeon Crawler Carl', source: 'goodreads', source_id: '9' },
    ],
  }
  render(<FieldGrid fields={{ title }} order={['title', 'subtitle']} level="edition"
    staging={{ book: 'B', scope: 'ed', records: { hardcover: ['1'], goodreads: ['9'] } }} />)

  expect(screen.getAllByText('subtitle may be in title')).toHaveLength(1)
  act(() => screen.getByText('Use “Dungeon Crawler Carl” as title').click())
  act(() => screen.getByText('Use “Deluxe Edition” as subtitle').click())

  const [titleChange, subtitleChange] = changeset.all()
  expect(titleChange).toMatchObject({ field: 'title', value: 'Dungeon Crawler Carl', chosenFrom: 'hardcover' })
  expect(titleChange.corrections).toEqual([{ source: 'hardcover', record: '1', current: 'Dungeon Crawler Carl: Deluxe Edition' }])
  expect(subtitleChange).toMatchObject({ field: 'subtitle', value: 'Deluxe Edition' })
  expect(subtitleChange.corrections).toEqual([
    { source: 'hardcover', record: '1', current: null },
    { source: 'goodreads', record: '9', current: null },
  ])
})
