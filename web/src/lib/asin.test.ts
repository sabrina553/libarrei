import { expect, test } from 'vitest'
import { asinNotes, editionFormat, storeAsin } from './asin'
import type { SourceName } from './format'

const v = (value: string, source: SourceName, source_id = value) => ({ value, source, source_id })

test('edition format only when sources agree', () => {
  expect(editionFormat([v('audiobook', 'hardcover'), v('audiobook', 'audible')])).toBe('audiobook')
  expect(editionFormat([v('audiobook', 'hardcover'), v('ebook', 'amazon')])).toBeNull()
})

test("audible's asin is the suggestion for an audiobook, alone", () => {
  const values = [v('B0DM64FRQW', 'hardcover'), v('B0DM68J1PP', 'audible')]
  expect(storeAsin(values, 'audiobook', () => 'audiobook')?.value).toBe('B0DM68J1PP')
})

test("amazon's kindle asin is the suggestion for an ebook, not its print listing", () => {
  const values = [v('B0KINDLE01', 'amazon'), v('B0OTHER001', 'goodreads')]
  expect(storeAsin(values, 'ebook', () => 'ebook')?.value).toBe('B0KINDLE01')
  expect(storeAsin(values, 'ebook', () => 'physical')).toBeNull()
  expect(storeAsin(values, 'physical', () => 'physical')).toBeNull()
})

test('notes from store checks', () => {
  const values = [v('B0DM64FRQW', 'hardcover'), v('B0DM68J1PP', 'audible')]
  const checks = { B0DM64FRQW: 'not_found', B0SAME0001: 'same_product' }
  expect(asinNotes('B0DM64FRQW', values, checks, 'audiobook')).toEqual([expect.objectContaining({ text: 'not found on Audible', warning: true })])
  expect(asinNotes('B0SAME0001', values, checks, 'audiobook')).toEqual([expect.objectContaining({ text: 'also valid', warning: false })])
  expect(asinNotes('B0DM68J1PP', values, checks, 'audiobook')).toEqual([])
})

test('a B0 asin on a print edition is suspicious', () => {
  expect(asinNotes('B0H8V4BRJD', [v('B0H8V4BRJD', 'goodreads')], {}, 'physical')[0].title)
    .toBe('ASIN looks like a Kindle/Audible ID on a print edition')
  expect(asinNotes('0261103342', [], {}, 'physical')).toEqual([])
})

test('notes name the Amazon stores that were checked', () => {
  const checks = { B0DT38PQYW: 'not_found', B0USONLY01: 'same_product' }
  const stores = { B0DT38PQYW: ['co.uk', 'com', 'ca'], B0USONLY01: ['com'] }
  expect(asinNotes('B0DT38PQYW', [], checks, 'ebook', stores)[0].text).toBe('no live listing on amazon.co.uk, .com, .ca')
  expect(asinNotes('B0USONLY01', [], checks, 'ebook', stores)[0].text).toBe('also valid on amazon.com')
})
