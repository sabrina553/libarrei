import { act, render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import { SlugsContext } from '../lib/links'
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

// Every source has a record, so gaps are real gaps rather than absent records.
const everyRecord = { book: 'B', scope: 'ed', records: { hardcover: ['1'], goodreads: ['2'], openlibrary: ['OL1M'], amazon: ['B0'] } }

test('colours cells that differ or are missing, with no majority to pick from', () => {
  render(<FieldGrid fields={{ pages }} order={['pages']} level="edition" staging={everyRecord} />)

  // One source each for 310 and 320, so neither is the majority and both differ.
  expect(screen.getByText('310').closest('td')).toHaveClass('differs')
  expect(screen.getByText('320').closest('td')).toHaveClass('differs')
  // Goodreads gives page counts but has none here; Amazon is only a reference, so its gap is plain.
  const [goodreads, amazon] = screen.getAllByText('—').map((gap) => gap.closest('td'))
  expect(goodreads).toHaveClass('missing')
  expect(amazon).not.toHaveClass('missing')
  expect(amazon).toHaveClass('reference')
  expect(screen.getByText('reference')).toBeInTheDocument()
  expect(screen.getByText('differs')).toBeInTheDocument()
  expect(screen.getByText('missing: GR')).toBeInTheDocument()
})

test('greys out a source with no record instead of marking its cells missing', () => {
  render(<FieldGrid fields={{ pages }} order={['pages', 'publisher']} level="edition"
    staging={{ book: 'B', scope: 'ed', records: { hardcover: ['1'], openlibrary: ['OL1M'], goodreads: ['2'] } }} />)

  // Amazon has no record: one note in its header, plain cells, and no "missing" for it.
  expect(screen.getAllByText('no record')).toHaveLength(1)
  expect(screen.getByText('no record').closest('th')).toHaveClass('norecord')
  const amazon = [...document.querySelectorAll('tbody tr')].map((r) => r.querySelectorAll('td')[3])
  for (const cell of amazon) expect(cell).toHaveClass('norecord')
  // Goodreads has a record but no page count, so that gap is still missing.
  expect(screen.getByText('missing: GR')).toBeInTheDocument()
})

test('only problems ignores sources with no record', () => {
  const language: Resolved = {
    value: 'en', source: 'hardcover', source_id: '1', conflict: false, alternatives: [],
    values: [{ value: 'en', source: 'hardcover', source_id: '1' }],
  }
  render(<FieldGrid fields={{ language }} order={['language']} level="edition" />)
  expect(screen.getByText(/0 of 1 fields/)).toBeInTheDocument()
})

test('highlights where a value departs from the majority', () => {
  const release: Resolved = {
    value: 468, source: 'hardcover', source_id: '1', conflict: true, alternatives: [],
    values: [
      { value: 468, source: 'hardcover', source_id: '1' },
      { value: 450, source: 'goodreads', source_id: '2' },
      { value: 468, source: 'openlibrary', source_id: 'OL1M' },
    ],
  }
  const { container } = render(<FieldGrid fields={{ pages: release }} order={['pages']} level="edition" />)

  const cells = container.querySelectorAll('tbody td')
  expect(cells[0]).toHaveClass('agrees')
  expect(cells[1]).toHaveClass('differs')
  expect(cells[1].querySelector('mark')).toHaveTextContent('5')
})

test('only problems hides rows where every source agrees', () => {
  const language: Resolved = {
    value: 'en', source: 'hardcover', source_id: '1', conflict: false, alternatives: [],
    values: (['hardcover', 'goodreads', 'openlibrary', 'audible', 'amazon'] as const).map((source) => ({ value: 'en', source, source_id: '1' })),
  }
  render(<FieldGrid fields={{ pages, language }} order={['pages', 'language']} level="edition" />)

  act(() => screen.getByLabelText(/Only problems/).click())
  expect(screen.queryByText('Language')).toBeNull()
  expect(screen.getByText('Pages')).toBeInTheDocument()
})

test('shows every field and tells unsupported fields apart from empty ones', () => {
  render(<FieldGrid fields={{ pages }} order={['title', 'duration_seconds', 'pages']} level="edition" staging={everyRecord} />)

  expect(screen.getByText('Title')).toBeInTheDocument()
  // Only Hardcover and Audible (in the Amazon column) give an audiobook length.
  const unsupported = screen.getAllByText('not provided')
  expect(unsupported).toHaveLength(2)
  expect(unsupported[0]).toHaveAttribute('title', 'Goodreads does not provide this field')
  // Empty: title in all four columns, duration on Hardcover and Amazon, pages on Goodreads and Amazon.
  expect(screen.getAllByText('—')).toHaveLength(8)
})

test('picking a value stages a correction for the source that disagrees', async () => {
  const { changeset } = await import('../lib/changeset')
  changeset.clear()
  render(<FieldGrid fields={{ pages }} order={['pages']} level="edition" staging={{ book: 'B', scope: 'ed', records: { hardcover: ['1'], openlibrary: ['OL1M'] } }} />)

  act(() => screen.getByText('310').closest('td')!.click())

  const [change] = changeset.all()
  expect(change.value).toBe(310)
  expect(change.corrections).toEqual([{ source: 'openlibrary', record: 'OL1M', current: 320 }])
})

test('labels every value with a link to its record', () => {
  const isbn13: Resolved = {
    value: '9780000000001', source: 'openlibrary', source_id: 'OL1M', conflict: false, alternatives: [],
    values: [
      { value: '9780000000001', source: 'openlibrary', source_id: 'OL1M' },
      { value: '9780000000001', source: 'openlibrary', source_id: 'OL2M' },
      { value: '9780000000001', source: 'hardcover', source_id: '5' },
    ],
  }
  render(
    <SlugsContext value={{ hardcover: 'the-hobbit' }}>
      <FieldGrid fields={{ isbn13 }} order={['isbn13']} level="edition" />
    </SlugsContext>,
  )

  expect(screen.getByText('OL1M')).toHaveAttribute('href', 'https://openlibrary.org/books/OL1M')
  expect(screen.getByText('OL2M')).toHaveAttribute('href', 'https://openlibrary.org/books/OL2M')
  // A lone record is labelled too, so every cell leads back to its source.
  expect(screen.getByText('5')).toHaveAttribute('href', 'https://hardcover.app/books/the-hobbit/editions/5')
})

test('without a slug a Hardcover record is labelled but not linked', () => {
  const pages: Resolved = {
    value: 300, source: 'hardcover', source_id: '5', conflict: false, alternatives: [],
    values: [{ value: 300, source: 'hardcover', source_id: '5' }],
  }
  render(<FieldGrid fields={{ pages }} order={['pages']} level="edition" />)
  expect(screen.getByText('5').tagName).toBe('SPAN')
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

test('the amazon column tags each value with the listing it came from', () => {
  const asin: Resolved = {
    value: 'B002GYI9C4', source: 'amazon', source_id: 'B002GYI9C4', conflict: false, alternatives: [],
    values: [
      { value: 'B002GYI9C4', source: 'amazon', source_id: 'B002GYI9C4' },
      { value: 'B004EW5KKU', source: 'audible', source_id: 'B004EW5KKU' },
    ],
  }
  const format: Resolved = {
    value: 'ebook', source: 'amazon', source_id: 'B002GYI9C4', conflict: false, alternatives: [],
    values: [
      { value: 'ebook', source: 'amazon', source_id: 'B002GYI9C4' },
      { value: 'audiobook', source: 'audible', source_id: 'B004EW5KKU' },
    ],
  }
  render(
    <SlugsContext value={{ amazon: 'co.uk', audible: 'co.uk' }}>
      <FieldGrid fields={{ asin, format }} order={['asin']} level="edition" />
    </SlugsContext>,
  )

  expect(screen.getByText('Amazon')).toBeInTheDocument()
  expect(screen.queryByText('Audible')).toBeInTheDocument()
  expect(screen.getByText('Kindle')).toBeInTheDocument()
  expect(screen.getAllByText('B002GYI9C4').find((e) => e.tagName === 'A'))
    .toHaveAttribute('href', 'https://www.amazon.co.uk/dp/B002GYI9C4')
  expect(screen.getAllByText('B004EW5KKU').find((e) => e.tagName === 'A'))
    .toHaveAttribute('href', 'https://www.audible.co.uk/pd/B004EW5KKU')
})

const agreed = (): Resolved => ({
  value: 310, source: 'hardcover', source_id: '1', conflict: true, alternatives: [],
  values: [
    { value: 310, source: 'hardcover', source_id: '1' },
    { value: 310, source: 'goodreads', source_id: '2' },
    { value: 320, source: 'openlibrary', source_id: 'OL1M' },
  ],
})

test('outlines the suggested cell and accepts every suggestion at once', async () => {
  const { changeset } = await import('../lib/changeset')
  changeset.clear()
  const language: Resolved = {
    value: 'en', source: 'hardcover', source_id: '1', conflict: false, alternatives: [],
    values: [{ value: 'en', source: 'hardcover', source_id: '1' }, { value: 'en', source: 'goodreads', source_id: '2' },
      { value: 'en', source: 'openlibrary', source_id: 'OL1M' }],
  }
  render(<FieldGrid fields={{ pages: agreed(), language }} order={['pages', 'language']} level="edition" staging={everyRecord} />)

  const outlined = document.querySelectorAll('.tick.suggested')
  // Pages and language each get one suggestion, on the first editable source holding it.
  expect(outlined).toHaveLength(2)
  expect(outlined[0].closest('td')).toHaveTextContent('310')
  // Language already agrees everywhere it is editable, so only pages needs accepting.
  act(() => screen.getByText('Accept suggestions (1)').click())
  const [change] = changeset.all()
  expect(change).toMatchObject({ field: 'pages', value: 310, chosenFrom: 'hardcover' })
  expect(change.corrections).toEqual([{ source: 'openlibrary', record: 'OL1M', current: 320 }])
  expect(screen.getByText('Accept suggestions (0)')).toBeDisabled()
})

test('accepting suggestions skips rows already staged', async () => {
  const { changeset } = await import('../lib/changeset')
  changeset.clear()
  render(<FieldGrid fields={{ pages: agreed() }} order={['pages']} level="edition" staging={everyRecord} />)
  act(() => (document.querySelectorAll('tbody td')[2] as HTMLElement).click())
  expect(screen.getByText('Accept suggestions (0)')).toBeDisabled()
  expect(changeset.all()[0].value).toBe(320)
})

test('an empty cell can be picked to say no value is correct', async () => {
  const { changeset } = await import('../lib/changeset')
  changeset.clear()
  render(<FieldGrid fields={{ pages }} order={['pages']} level="edition" staging={everyRecord} />)

  const gap = screen.getAllByText('—')[0].closest('td')!
  act(() => gap.click())
  const [change] = changeset.all()
  expect(change).toMatchObject({ value: null, chosenFrom: 'goodreads' })
  // Only editable sources with a value are corrected; Amazon is a reference store.
  expect(change.corrections.map((c) => c.source)).toEqual(['hardcover', 'openlibrary'])
  expect(gap).toHaveClass('picked')
  act(() => gap.click())
  expect(changeset.all()).toEqual([])
})
