import { expect, test } from 'vitest'
import { formatValue } from './format'

test('formats each kind of field value', () => {
  expect(formatValue('Dune')).toBe('Dune')
  expect(formatValue(412)).toBe('412')
  expect(formatValue(null)).toBe('—')
  expect(formatValue(['Fantasy', 'Classics'])).toBe('Fantasy, Classics')
  expect(formatValue([{ name: 'Ann Napolitano', role: 'author' }, { name: 'Jane Doe', role: 'narrator' }]))
    .toBe('Ann Napolitano, Jane Doe (narrator)')
  expect(formatValue([{ name: 'Mistborn', position: '1' }])).toBe('Mistborn #1')
})
