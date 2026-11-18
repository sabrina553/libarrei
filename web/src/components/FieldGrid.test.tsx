import { render, screen } from '@testing-library/react'
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
  render(<FieldGrid fields={{ pages }} order={['title', 'pages']} />)

  expect(screen.getByText('310').closest('td')).toHaveClass('chosen')
  expect(screen.getByText('320').closest('td')).not.toHaveClass('chosen')
  expect(screen.getByText('conflict')).toBeInTheDocument()
  // Goodreads gave nothing, and the missing title row is skipped.
  expect(screen.getAllByText('—')).toHaveLength(1)
  expect(screen.queryByText('Title')).toBeNull()
})

test('picking a value stages a correction for the source that disagrees', async () => {
  const { changeset } = await import('../lib/changeset')
  changeset.clear()
  render(<FieldGrid fields={{ pages }} order={['pages']} staging={{ book: 'B', scope: 'ed', records: { hardcover: ['1'], openlibrary: ['OL1M'] } }} />)

  screen.getAllByText('Use this')[0].click()

  const [change] = changeset.all()
  expect(change.value).toBe(310)
  expect(change.corrections).toEqual([{ source: 'openlibrary', record: 'OL1M', current: 320 }])
})
