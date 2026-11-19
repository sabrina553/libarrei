import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, test } from 'vitest'
import { amazonCookie, getToken } from '../settings/token'
import { Settings } from './Settings'

beforeEach(() => localStorage.clear())

test('saving then forgetting a token', () => {
  render(<Settings />)
  fireEvent.change(screen.getByLabelText(/token/i), { target: { value: 'secret' } })
  fireEvent.submit(screen.getByLabelText(/token/i))
  expect(getToken()).toBe('secret')

  fireEvent.click(screen.getByText('Forget token'))
  expect(getToken()).toBeNull()
})

test('the amazon cookie is saved separately', () => {
  render(<Settings />)
  fireEvent.change(screen.getByLabelText(/cookie/i), { target: { value: 'session-id=1' } })
  fireEvent.submit(screen.getByLabelText(/cookie/i))
  expect(amazonCookie.get()).toBe('session-id=1')
  expect(getToken()).toBeNull()

  fireEvent.click(screen.getByText('Forget cookie'))
  expect(amazonCookie.get()).toBeNull()
})
