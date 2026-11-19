import { beforeEach, expect, test } from 'vitest'
import { forgetToken, getToken, setToken } from './token'

beforeEach(() => localStorage.clear())

test('saves, trims and forgets the token', () => {
  expect(getToken()).toBeNull()
  setToken('  abc  ')
  expect(getToken()).toBe('abc')
  forgetToken()
  expect(getToken()).toBeNull()
})
