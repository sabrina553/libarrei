import type { components } from '../api/schema'
import { buildChange, changeset, useChangeset } from '../lib/changeset'
import { formatDuration, formatValue, SOURCE_LABELS, SOURCES, type SourceName } from '../lib/format'
import { useState } from 'react'
import { inlineDiff, rowStates, type CellState } from '../lib/cellStates'
import { provides, type Level } from './capabilities'
import { DescriptionValue } from './DescriptionValue'
import { RecordLink } from './RecordLink'
import { splitKey, titleSplits, type TitleSplit } from './titleSplit'

export type Resolved = components['schemas']['Resolved']

const LABELS: Record<string, string> = {
  original_release_date: 'First published',
  release_date: 'Release date',
  cover_url: 'Cover',
  isbn13: 'ISBN-13',
  isbn10: 'ISBN-10',
  asin: 'ASIN',
  format_detail: 'Format (as given)',
  duration_seconds: 'Duration',
}

export function fieldLabel(name: string): string {
  return LABELS[name] ?? name.charAt(0).toUpperCase() + name.slice(1).replaceAll('_', ' ')
}

type Props = {
  fields: Record<string, Resolved>
  // Fields in display order; every one gets a row, even when no source filled it.
  order: string[]
  // Decides which fields each source can provide at all.
  level: Level
  // When given, values can be picked to stage corrections.
  staging?: { book: string; scope: string; records: Partial<Record<SourceName, string[]>> }
}

/** Fields down the side, sources across the top, like a side-by-side diff. */
export function FieldGrid({ fields, order, level, staging }: Props) {
  const staged = useChangeset()
  const [onlyProblems, setOnlyProblems] = useState(false)
  const splits = titleSplits(fields)
  // Stages a value that no source holds verbatim, crediting the source whose title it came from.
  const stageDerived = staging && ((field: string, from: SourceValue, value: string) => {
    const current = staged.find((c) => c.id === `${staging.scope}::${field}`)
    if (current?.chosenFrom === from.source && current.value === value) return changeset.unstage(current.id)
    const values = fields[field]?.values ?? []
    const change = buildChange(staging.book, staging.scope, field, { ...from, value }, values, staging.records)
    // The source the split came from holds the unsplit value, so its own record needs correcting too.
    const own = values.find((v) => v.source === from.source && v.source_id === from.source_id)
    if (formatValue(own?.value ?? null) !== value)
      change.corrections.unshift({ source: from.source, record: from.source_id, current: own?.value ?? null })
    changeset.stage(change)
  })
  const isStaged = (field: string, value: string) =>
    !!staging && staged.some((c) => c.id === `${staging.scope}::${field}` && c.value === value)
  const rows = order.map((name) => {
    const resolved = fields[name]
    return { name, resolved, ...rowStates(name, resolved?.values ?? [], (s) => provides(level, s, name)) }
  })
  const problems = rows.filter((r) => r.problem).length
  return (
    <>
      <label className="only-problems">
        <input type="checkbox" checked={onlyProblems} onChange={(e) => setOnlyProblems(e.target.checked)} />
        Only problems ({problems} of {rows.length} fields differ or are missing)
      </label>
      <table className="grid">
        <thead>
          <tr>
            <th>Field</th>
            {SOURCES.map((s) => <th key={s}>{SOURCE_LABELS[s]}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.filter((r) => !onlyProblems || r.problem).map(({ name, resolved, states, modal }) => {
            const counts = Object.values(states)
            const differs = counts.includes('differs')
            const missing = counts.includes('missing')
            const id = staging && `${staging.scope}::${name}`
            const pick = staged.find((c) => c.id === id)
            return (
              <tr key={name}>
                <th scope="row">
                  {fieldLabel(name)}
                  {differs && <span className="badge differs" title="Sources disagree">differs</span>}
                  {missing && <span className="badge missing" title="Some sources have no value">missing</span>}
                </th>
                {SOURCES.map((source) => {
                  const state = states[source]
                  if (state === 'unsupported')
                    return <td key={source} className="unsupported" title={`${SOURCE_LABELS[source]} does not provide this field`}>not provided</td>
                  if (state === 'missing' || state === 'empty' || !resolved)
                    return <td key={source} className={state} title={state === 'missing' ? 'No value here, though another source has one' : 'No source has a value'}>—</td>
                  return (
                    <Cell
                      key={source} name={name} source={source} level={level} resolved={resolved} state={state} modal={modal}
                      // A split title staged from this source is not this cell's own value.
                      picked={pick?.chosenFrom === source && resolved.values.some((v) =>
                        v.source === source && formatValue(v.value) === formatValue(pick.value))}
                      onPick={staging && ((value) => pick?.chosenFrom === source
                        ? changeset.unstage(pick.id)
                        : changeset.stage(buildChange(staging.book, staging.scope, name, value, resolved.values, staging.records)))}
                      splitFor={name === 'title' ? (v) => splits.get(splitKey(v)) : undefined}
                      onSplitPick={stageDerived} isStaged={isStaged}
                    />
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
    </>
  )
}

type SourceValue = Resolved['values'][number]

type CellProps = {
  name: string
  source: SourceName
  level: Level
  resolved: Resolved
  state: CellState
  modal: string | null
  picked: boolean
  onPick?: (value: SourceValue) => void
  splitFor?: (value: SourceValue) => TitleSplit | undefined
  onSplitPick?: (field: string, from: SourceValue, value: string) => void
  isStaged: (field: string, value: string) => boolean
}

function Cell({ name, source, level, resolved, state, modal, picked, onPick, splitFor, onSplitPick, isStaged }: CellProps) {
  const values = (resolved.values ?? []).filter((v) => v.source === source)
  const classes = [state, onPick && 'pickable', picked && 'picked'].filter(Boolean).join(' ')
  const pick = onPick && (() => onPick(values[0]))
  return (
    <td
      className={classes}
      title={onPick ? (picked ? 'Staged; click to undo' : 'Click to use this value') : undefined}
      // Links and buttons inside the cell do their own thing rather than picking the value.
      onClick={pick && ((e) => { if (!isInner(e.target, e.currentTarget)) pick() })}
      onKeyDown={pick && ((e) => {
        if ((e.key === 'Enter' || e.key === ' ') && !isInner(e.target, e.currentTarget)) { e.preventDefault(); pick() }
      })}
      tabIndex={onPick ? 0 : undefined}
      role={onPick ? 'button' : undefined}
      aria-pressed={onPick ? picked : undefined}
    >
      {values.map((v, i) => (
        <div key={i} className={name === 'description' ? 'long' : undefined}>
          {name === 'description' ? <DescriptionValue value={v} values={resolved.values} />
            : <Value name={name} value={v.value} modal={state === 'differs' ? modal : null} />}
          <RecordLink level={level} value={v} />
          <SplitHint value={v} split={splitFor?.(v)} onPick={onSplitPick} isStaged={isStaged} />
        </div>
      ))}
      {name === 'description' && resolved.source === source && resolved.licence && <div className="licence">{resolved.licence}</div>}
      {picked && <span className="tick" aria-hidden>✓</span>}
    </td>
  )
}

function isInner(target: EventTarget, cell: Element): boolean {
  const inner = (target as Element).closest?.('a, button')
  return !!inner && inner !== cell && cell.contains(inner)
}

function Value({ name, value, modal }: { name: string; value: unknown; modal: string | null }) {
  if (name === 'cover_url') return <img src={String(value)} alt="" loading="lazy" />
  const text = name === 'duration_seconds' ? formatDuration(Number(value)) : formatValue(value)
  // Long text needs a word-level diff; a character diff of short values shows typos and number slips.
  if (!modal || name === 'description' || text.length > 120) return <>{text}</>
  const [before, changed, after] = inlineDiff(text, modal)
  return <>{before}<mark>{changed}</mark>{after}</>
}

type SplitHintProps = {
  value: SourceValue
  split?: TitleSplit
  onPick?: (field: string, from: SourceValue, value: string) => void
  isStaged: (field: string, value: string) => boolean
}

function SplitHint({ value, split, onPick, isStaged }: SplitHintProps) {
  if (!split) return null
  const statement = split.field === 'edition_statement'
  const options = [['title', split.title], [split.field, split.subtitle]] as const
  return (
    <>
      {statement
        ? <span className="badge hint" title="The part after the colon reads like an edition statement">edition may be in title</span>
        : <span className="badge hint" title="Another source's title or subtitle suggests this title includes the subtitle">subtitle may be in title</span>}
      {onPick && options.map(([field, text]) => (
        <button key={field} className="split" onClick={() => onPick(field, value, text)} aria-pressed={isStaged(field, text)}>
          {isStaged(field, text) ? 'Staged ✓' : `Use “${text}” as ${fieldLabel(field).toLowerCase()}`}
        </button>
      ))}
    </>
  )
}
