import { expect, test } from 'vitest'
import { recordUrl } from './links'

test('each source links works and editions to its own pages', () => {
  expect(recordUrl('work', 'openlibrary', 'OL1W')).toBe('https://openlibrary.org/works/OL1W')
  expect(recordUrl('edition', 'openlibrary', 'OL1M')).toBe('https://openlibrary.org/books/OL1M')
  expect(recordUrl('work', 'goodreads', '7')).toBe('https://www.goodreads.com/work/editions/7')
  expect(recordUrl('edition', 'goodreads', '8')).toBe('https://www.goodreads.com/book/show/8')
  expect(recordUrl('work', 'hardcover', '1', { hardcover: 'the-hobbit' })).toBe('https://hardcover.app/books/the-hobbit')
  expect(recordUrl('edition', 'hardcover', '2', { hardcover: 'the-hobbit' }))
    .toBe('https://hardcover.app/books/the-hobbit/editions/2')
})

test('audible links to the store the record came from', () => {
  expect(recordUrl('edition', 'audible', 'B004EW5KKU', { audible: 'co.uk' })).toBe('https://www.audible.co.uk/pd/B004EW5KKU')
  expect(recordUrl('edition', 'audible', 'B004EW5KKU')).toBeUndefined()
})

test('hardcover needs a slug, and odd ids cannot escape the path', () => {
  expect(recordUrl('edition', 'hardcover', '2')).toBeUndefined()
  expect(recordUrl('edition', 'openlibrary', '../x?y')).toBe('https://openlibrary.org/books/..%2Fx%3Fy')
})
