import { expect, test } from 'vitest'
import { baseline, blocksOf, changedRanges, compare, flatText, similarity } from './description'

test('the baseline is the text most sources agree on, ignoring whitespace', () => {
  expect(baseline(['One  two.', 'Three.', 'One two.'])).toBe('One two.')
})

test('with no majority and nothing in common the first source is the baseline', () => {
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

test('with no majority the baseline is the text closest to the others', () => {
  expect(baseline(['A hobbit goes on a journey.', 'Dragons and gold.', 'A hobbit goes on a long journey.'])).toBe('A hobbit goes on a journey.')
})

test('similarity is the share of words in common, ignoring case and punctuation', () => {
  expect(similarity('The Hobbit.', 'the hobbit')).toBe(1)
  expect(similarity('one two', 'three four')).toBe(0)
  expect(similarity('a b c d', 'a b c e')).toBe(0.75)
})

test('shared words are never highlighted, even when repeated elsewhere', () => {
  const text = 'A brave hobbit went to the mountain with the dwarves.'
  const ranges = changedRanges(text, 'A hobbit went to the mountain with dwarves and a wizard.')
  const marked = ranges.map(([a, b]) => text.slice(a, b))
  expect(marked).toContain('brave')
  for (const word of ['hobbit', 'mountain', 'dwarves.']) expect(marked).not.toContain(word)
})

test('a close variant is diffed; a different blurb is flagged and not highlighted', () => {
  const base = 'Bilbo the hobbit sets out with dwarves to win back their gold from a dragon.'
  expect(compare('Bilbo the hobbit sets out with thirteen dwarves to win back their gold from a dragon.', base))
    .toMatchObject({ distinct: false, ranges: [[31, 39]] })
  expect(compare('An epic prequel to the greatest fantasy saga of all time.', base)).toEqual({ ranges: [], distinct: true })
  expect(compare(base, base)).toEqual({ ranges: [], distinct: false })
})
