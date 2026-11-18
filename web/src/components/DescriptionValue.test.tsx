import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import { splitByRanges, type Block } from '../lib/description'
import { DescriptionValue } from './DescriptionValue'

const run = (text: string, bold = false, italic = false) => ({ text, bold, italic })
const value = (text: string, formatted: Block[] | null = null, source: 'goodreads' | 'hardcover' | 'openlibrary' = 'goodreads') =>
  ({ value: text, source, source_id: '1', formatted })

test('renders formatting as elements, with lists and line breaks', () => {
  const v = value('Bold and italic\nnext\n\na\nb', [
    { kind: 'paragraph', runs: [run('Bold', true), run(' and '), run('italic', false, true), run('\nnext')] },
    { kind: 'item', runs: [run('a')] },
    { kind: 'item', runs: [run('b')] },
  ])
  const { container } = render(<DescriptionValue value={v} values={[v]} />)
  expect(container.querySelector('strong')).toHaveTextContent('Bold')
  expect(container.querySelector('em')).toHaveTextContent('italic')
  expect(container.querySelector('br')).not.toBeNull()
  expect(container.querySelectorAll('ul > li')).toHaveLength(2)
})

test('markup inside text stays text', () => {
  const evil = '<img src=x onerror="alert(1)"><script>alert(2)</script><a href="javascript:alert(3)">x</a>'
  const v = value(evil, [{ kind: 'paragraph', runs: [run(evil, true)] }])
  const { container } = render(<DescriptionValue value={v} values={[v]} />)
  expect(container.querySelector('img, script, a, [onerror]')).toBeNull()
  expect(container).toHaveTextContent(evil)
})

test('highlights words that differ from the most common text', () => {
  const same = value('A quiet hobbit.', null, 'hardcover')
  const other = value('A noisy hobbit.', null, 'openlibrary')
  const { container } = render(<DescriptionValue value={other} values={[value('A quiet hobbit.'), same, other]} />)
  expect([...container.querySelectorAll('mark')].map((m) => m.textContent)).toEqual(['noisy'])

  const { container: agreeing } = render(<DescriptionValue value={same} values={[value('A quiet hobbit.'), same, other]} />)
  expect(agreeing.querySelector('mark')).toBeNull()
})

test('long descriptions collapse behind Show more', () => {
  const v = value('word '.repeat(100).trim())
  const { container } = render(<DescriptionValue value={v} values={[v]} />)
  expect(container.querySelector('.collapsed')).not.toBeNull()
  fireEvent.click(screen.getByText('Show more'))
  expect(container.querySelector('.collapsed')).toBeNull()
  expect(screen.getByText('Show less')).toBeInTheDocument()
})

test('ranges split a run at their edges', () => {
  expect(splitByRanges('abcdef', 10, [[12, 14]])).toEqual([['ab', false], ['cd', true], ['ef', false]])
})
