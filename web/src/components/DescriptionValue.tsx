import { useState, type ReactNode } from 'react'
import type { components } from '../api/schema'
import { baseline, blocksOf, changedRanges, flatText, splitByRanges, type Block, type Range, type Run } from '../lib/description'

type SourceValue = components['schemas']['Alternative']

// Roughly four lines of a grid cell; shorter text has nothing to hide.
const COLLAPSE_AT = 280

type Props = {
  value: SourceValue
  // Every source's value, to find the text this one is compared against.
  values: SourceValue[]
}

/**
 * A description rendered from its safe structure as React elements, never as
 * HTML, with the words that differ from most sources highlighted.
 */
export function DescriptionValue({ value, values }: Props) {
  const [expanded, setExpanded] = useState(false)
  const blocks = blocksOf(value.formatted, String(value.value))
  const flat = flatText(blocks)
  const base = baseline(values.map((v) => flatText(blocksOf(v.formatted, String(v.value)))))
  const ranges = changedRanges(flat, base)
  const long = flat.length > COLLAPSE_AT || blocks.length > 3
  return (
    <div className="description">
      <div className={long && !expanded ? 'description-body collapsed' : 'description-body'}>
        {renderBlocks(blocks, ranges)}
      </div>
      {long && (
        <button type="button" className="link" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}>
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  )
}

function renderBlocks(blocks: Block[], ranges: Range[]): ReactNode[] {
  const out: ReactNode[] = []
  let items: ReactNode[] = []
  let offset = 0
  blocks.forEach((block, i) => {
    const content = renderRuns(block.runs, offset, ranges)
    offset += block.runs.reduce((n, r) => n + r.text.length, 0) + 1
    if (block.kind === 'item') {
      items.push(<li key={i}>{content}</li>)
      return
    }
    if (items.length) out.push(<ul key={`list-${i}`}>{items}</ul>)
    items = []
    out.push(<p key={i}>{content}</p>)
  })
  if (items.length) out.push(<ul key="list-end">{items}</ul>)
  return out
}

function renderRuns(runs: Run[], start: number, ranges: Range[]): ReactNode[] {
  let offset = start
  return runs.map((run, i) => {
    const pieces = splitByRanges(run.text, offset, ranges).map(([text, changed], j) => {
      const lines = text.split('\n').flatMap((line, k) => (k ? [<br key={`br${k}`} />, line] : [line]))
      return changed ? <mark key={j} className="diff">{lines}</mark> : <span key={j}>{lines}</span>
    })
    offset += run.text.length
    let node: ReactNode = pieces
    if (run.italic) node = <em>{node}</em>
    if (run.bold) node = <strong>{node}</strong>
    return <span key={i}>{node}</span>
  })
}
