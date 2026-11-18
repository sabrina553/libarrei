import { expect, test } from 'vitest'
import { isEditionStatement, titleSplits } from './titleSplit'

type Source = 'hardcover' | 'goodreads' | 'openlibrary'

const resolved = (values: [string, Source][]) => ({
  value: values[0][0], source: values[0][1], source_id: '1', alternatives: [], conflict: true,
  values: values.map(([value, source]) => ({ value, source, source_id: '1' })),
})

test('splits a title when another source has the short title', () => {
  const splits = titleSplits({ title: resolved([['Dungeon Crawler Carl: A LitRPG', 'hardcover'], ['Dungeon Crawler Carl', 'goodreads']]) })
  expect(splits.get('hardcover::1')).toEqual({ title: 'Dungeon Crawler Carl', subtitle: 'A LitRPG', field: 'subtitle' })
  expect(splits.size).toBe(1)
})

test('splits a title when a subtitle matches the tail', () => {
  const splits = titleSplits({ title: resolved([['Circe: a novel', 'openlibrary']]), subtitle: resolved([['A Novel', 'hardcover']]) })
  expect(splits.get('openlibrary::1')).toEqual({ title: 'Circe', subtitle: 'a novel', field: 'subtitle' })
})

test('leaves a colon title alone when nothing backs the split', () => {
  expect(titleSplits({ title: resolved([['Star Wars: Thrawn', 'hardcover'], ['Thrawn', 'goodreads']]) }).size).toBe(0)
})

test('offers an edition statement as one, even without another source', () => {
  const splits = titleSplits({ title: resolved([['Dungeon Crawler Carl: Deluxe Edition', 'hardcover']]) })
  expect(splits.get('hardcover::1')).toEqual({ title: 'Dungeon Crawler Carl', subtitle: 'Deluxe Edition', field: 'edition_statement' })
})

test.each([
  'Deluxe Edition', '2nd ed.', '50th Anniversary Edition', 'Collector’s Edition', "Collector's Edition",
  'Revised', 'Illustrated Edition', 'Revised and Expanded Edition',
])('%s is an edition statement', (text) => {
  expect(isEditionStatement(text)).toBe(true)
})

test.each(['A Novel', 'The Last Edition', 'There and Back Again', 'Edition'])('%s is not an edition statement', (text) => {
  expect(isEditionStatement(text)).toBe(false)
})
