import { expect, test } from 'vitest'
import { paramsFromQuery, queryFromParams } from './query'

test('round-trips a search through the URL', () => {
  const params = paramsFromQuery({ title: ' the hobbit ', author: 'tolkien', isbn: '' })
  expect(params).toBe('title=the+hobbit&author=tolkien')
  expect(queryFromParams(new URLSearchParams(params))).toEqual({ isbn: null, title: 'the hobbit', author: 'tolkien' })
})

test('a search needs a title or an ISBN', () => {
  expect(queryFromParams(new URLSearchParams('author=tolkien'))).toBeNull()
})
