import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, test } from 'vitest'
import { getToken } from '../settings/token'
import { Settings } from './Settings'

beforeEach(() => localStorage.clear())

test('saving then forgetting a token', () => {
  render(<Settings />)
  fireEvent.change(screen.getByLabelText(/token/i), { target: { value: 'secret' } })
  fireEvent.click(screen.getByText('Save'))
  expect(getToken()).toBe('secret')

  fireEvent.click(screen.getByText('Forget token'))
  expect(getToken()).toBeNull()
})
