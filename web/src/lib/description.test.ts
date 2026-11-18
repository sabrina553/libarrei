import { expect, test } from 'vitest'
import { baseline, blocksOf, changedRanges, flatText } from './description'

test('the baseline is the text most sources agree on, ignoring whitespace', () => {
  expect(baseline(['One  two.', 'Three.', 'One two.'])).toBe('One two.')
})

test('with no majority the first source is the baseline', () => {
  expect(baseline(['A.', 'B.', 'C.'])).toBe('A.')
  expect(baseline([])).toBeNull()
})

test('changed ranges mark only the words the baseline lacks', () => {
  const text = 'The quick red fox.'
  const ranges = changedRanges(text, 'The quick brown fox.')
  expect(ranges.map(([a, b]) => text.slice(a, b))).toEqual(['red'])
  expect(changedRanges('Same  words.', 'Same words.')).toEqual([])
  expect(changedRanges('Anything', null)).toEqual([])
})

test('plain text falls back to blank-line paragraphs', () => {
  const blocks = blocksOf(null, 'One.\n\nTwo.')
  expect(blocks).toHaveLength(2)
  expect(flatText(blocks)).toBe('One.\nTwo.')
})
