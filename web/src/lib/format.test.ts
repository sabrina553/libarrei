import { expect, test } from 'vitest'
import { formatDuration, formatValue } from './format'

test('formats each kind of field value', () => {
  expect(formatValue('Dune')).toBe('Dune')
  expect(formatValue(412)).toBe('412')
  expect(formatValue(null)).toBe('—')
  expect(formatValue(['Fantasy', 'Classics'])).toBe('Fantasy, Classics')
  expect(formatValue([{ name: 'Ann Napolitano', role: 'author' }, { name: 'Jane Doe', role: 'narrator' }]))
    .toBe('Ann Napolitano, Jane Doe (narrator)')
  expect(formatValue([{ name: 'Mistborn', position: '1' }])).toBe('Mistborn #1')
})

test('formats a duration as hours and minutes', () => {
  expect(formatDuration(37800)).toBe('10:30')
  expect(formatDuration(3599)).toBe('1:00')
  expect(formatDuration(300)).toBe('0:05')
  expect(formatDuration(0)).toBe('—')
})

test('formats identifiers with their scheme', () => {
  expect(formatValue([{ scheme: 'goodreads', value: '123' }, { scheme: 'oclc', value: '9' }])).toBe('goodreads: 123, oclc: 9')
})
