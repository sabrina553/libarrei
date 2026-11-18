import type { components } from '../api/schema'
import { buildChange, changeset, useChangeset } from '../lib/changeset'
import { columnOf, COLUMN_ABBREVIATIONS, COLUMN_LABELS, COLUMNS, isReference, REFERENCE_SOURCES, formatDuration, formatValue, storeTag, type ColumnName, type SourceName } from '../lib/format'
import { useState } from 'react'
import { inlineDiff, missingColumns, rowStates, type CellState } from '../lib/cellStates'
import { columnProvides, type Level } from './capabilities'
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
    if (formatValue(own?.value ?? null) !== value && !REFERENCE_SOURCES.has(from.source))
      change.corrections.unshift({ source: from.source, record: from.source_id, current: own?.value ?? null })
    changeset.stage(change)
  })
  const isStaged = (field: string, value: string) =>
    !!staging && staged.some((c) => c.id === `${staging.scope}::${field}` && c.value === value)
  const hasRecord = recordCheck(fields, staging?.records)
  const rows = order.map((name) => {
    const resolved = fields[name]
    return { name, resolved, ...rowStates(name, resolved?.values ?? [], (c) => columnProvides(level, c, name), hasRecord) }
  })
  // Each record's format, so values in the shared Amazon column can say which listing they came from.
  const formats = new Map((fields.format?.values ?? []).map((v) => [`${v.source}:${v.source_id}`, v.value]))
  const tag = (v: SourceValue) => storeTag(v.source, formats.get(`${v.source}:${v.source_id}`))
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
            {COLUMNS.map((c) => !hasRecord(c)
              ? <th key={c} className="norecord">{COLUMN_LABELS[c]} <span className="note">no record</span></th>
              : isReference(c)
                ? <th key={c} className="reference" title="A store listing, read for reference: it votes but is never corrected">
                    {COLUMN_LABELS[c]} <span className="note">reference</span>
                  </th>
                : <th key={c}>{COLUMN_LABELS[c]}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.filter((r) => !onlyProblems || r.problem).map(({ name, resolved, states, modal }) => {
            const differs = Object.values(states).includes('differs')
            const missing = missingColumns(states)
            const id = staging && `${staging.scope}::${name}`
            const pick = staged.find((c) => c.id === id)
            return (
              <tr key={name}>
                <th scope="row">
                  {fieldLabel(name)}
                  {differs && <span className="badge differs" title="Sources disagree">differs</span>}
                  {missing.length > 0 && (
                    <span className="badge missing" title={`No value from ${missing.map((c) => COLUMN_LABELS[c]).join(', ')}`}>
                      missing: {missing.map((c) => COLUMN_ABBREVIATIONS[c]).join(', ')}
                    </span>
                  )}
                </th>
                {COLUMNS.map((source) => {
                  const state = states[source]
                  if (state === 'norecord')
                    return <td key={source} className="norecord" title={`${COLUMN_LABELS[source]} has no record here`}>—</td>
                  if (state === 'unsupported')
                    return <td key={source} className="unsupported" title={`${COLUMN_LABELS[source]} does not provide this field`}>not provided</td>
                  if (state === 'missing' || state === 'empty' || !resolved)
                    return <td key={source} className={[state, isReference(source) && 'reference'].filter(Boolean).join(' ')} title={gapTitle(state, source)}>—</td>
                  return (
                    <Cell
                      key={source} name={name} source={source} level={level} resolved={resolved} state={state} modal={modal}
                      // A split title staged from this source is not this cell's own value.
                      picked={!!pick && columnOf(pick.chosenFrom) === source && resolved.values.some((v) =>
                        v.source === pick.chosenFrom && formatValue(v.value) === formatValue(pick.value))}
                      onPick={staging && ((value) => pick && columnOf(pick.chosenFrom) === source
                        ? changeset.unstage(pick.id)
                        : changeset.stage(buildChange(staging.book, staging.scope, name, value, resolved.values, staging.records)))}
                      splitFor={name === 'title' ? (v) => splits.get(splitKey(v)) : undefined}
                      onSplitPick={stageDerived} isStaged={isStaged} tag={tag}
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

function gapTitle(state: CellState, column: ColumnName): string {
  if (state === 'missing') return 'No value here, though another source has one'
  if (isReference(column)) return 'No value in this reference store'
  return 'No source has a value'
}

/**
 * Whether a column has a record here: from the staging records when known,
 * otherwise from whether it gave a value for any field.
 */
function recordCheck(fields: Record<string, Resolved>, records?: Partial<Record<SourceName, string[]>>) {
  const seen = new Set<ColumnName>()
  if (records) {
    for (const [source, ids] of Object.entries(records)) if (ids?.length) seen.add(columnOf(source as SourceName))
  }
  for (const f of Object.values(fields)) for (const v of f.values ?? []) seen.add(columnOf(v.source))
  return (column: ColumnName) => seen.has(column)
}

type CellProps = {
  name: string
  source: ColumnName
  level: Level
  resolved: Resolved
  state: CellState
  modal: string | null
  picked: boolean
  onPick?: (value: SourceValue) => void
  splitFor?: (value: SourceValue) => TitleSplit | undefined
  onSplitPick?: (field: string, from: SourceValue, value: string) => void
  isStaged: (field: string, value: string) => boolean
  tag: (value: SourceValue) => string | undefined
}

function Cell({ name, source, level, resolved, state, modal, picked, onPick, splitFor, onSplitPick, isStaged, tag }: CellProps) {
  const values = (resolved.values ?? []).filter((v) => columnOf(v.source) === source)
  const classes = [state, isReference(source) && 'reference', onPick && 'pickable', picked && 'picked'].filter(Boolean).join(' ')
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
          {tag(v) && <span className="badge store">{tag(v)}</span>}
          <RecordLink level={level} value={v} />
          <SplitHint value={v} split={splitFor?.(v)} onPick={onSplitPick} isStaged={isStaged} />
        </div>
      ))}
      {name === 'description' && columnOf(resolved.source) === source && resolved.licence && <div className="licence">{resolved.licence}</div>}
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
