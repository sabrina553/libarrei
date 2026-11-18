import type { components } from '../api/schema'
import { buildChange, changeset, useChangeset } from '../lib/changeset'
import { columnOf, COLUMN_ABBREVIATIONS, COLUMN_LABELS, COLUMN_SOURCES, COLUMNS, isReference, REFERENCE_SOURCES, formatDuration, formatValue, storeTag, type ColumnName, type SourceName } from '../lib/format'
import { useState } from 'react'
import { inlineDiff, missingColumns, rowStates, suggestion, type CellState } from '../lib/cellStates'
import { asinNotes, editionFormat, storeAsin, type AsinNote } from '../lib/asin'
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
  // Catalogue ASINs checked against the store, from the API's per-edition asin_checks.
  asinChecks?: Record<string, string>
}

/** Fields down the side, sources across the top, like a side-by-side diff. */
export function FieldGrid({ fields, order, level, staging, asinChecks = {} }: Props) {
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
  // Each record's format, so values in the shared Amazon column can say which listing they came from.
  const formats = new Map((fields.format?.values ?? []).map((v) => [`${v.source}:${v.source_id}`, v.value]))
  const recordFormat = (v: SourceValue) => formats.get(`${v.source}:${v.source_id}`)
  const tag = (v: SourceValue) => storeTag(v.source, recordFormat(v))
  const format = editionFormat(fields.format?.values ?? [])
  const suggest = (name: string, values: SourceValue[]) =>
    (name === 'asin' ? storeAsin(values, format, recordFormat) : null) ?? suggestion(name, values)
  const notesFor = (v: SourceValue) => asinNotes(String(v.value), fields.asin?.values ?? [], asinChecks, format)
  const rows = order.map((name) => {
    const resolved = fields[name]
    const values = resolved?.values ?? []
    return { name, resolved, suggested: suggest(name, values), ...rowStates(name, values, (c) => columnProvides(level, c, name), hasRecord) }
  })
  const change = (name: string, pick: SourceValue) =>
    buildChange(staging!.book, staging!.scope, name, pick, fields[name]?.values ?? [], staging!.records)
  // Rows already staged, or where no editable source needs correcting, are left alone.
  const acceptable = staging ? rows.flatMap(({ name, suggested }) => {
    if (!suggested || staged.some((c) => c.id === `${staging.scope}::${name}`)) return []
    const c = change(name, suggested)
    return c.corrections.length ? [c] : []
  }) : []
  // "No value is correct": a gap picked as the answer, credited to the column's record.
  const emptyPick = (column: ColumnName): SourceValue => {
    const source = COLUMN_SOURCES[column].find((s) => staging?.records[s]?.length) ?? COLUMN_SOURCES[column][0]
    return { value: null, source, source_id: staging?.records[source]?.[0] ?? '' }
  }
  const problems = rows.filter((r) => r.problem).length
  return (
    <>
      <label className="only-problems">
        <input type="checkbox" checked={onlyProblems} onChange={(e) => setOnlyProblems(e.target.checked)} />
        Only problems ({problems} of {rows.length} fields differ or are missing)
      </label>
      {staging && (
        <button type="button" className="secondary accept" disabled={!acceptable.length}
          onClick={() => acceptable.forEach((c) => changeset.stage(c))}
          title="Stage the suggested value (outlined ✓) for every field that needs correcting">
          Accept suggestions ({acceptable.length})
        </button>
      )}
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
          {rows.filter((r) => !onlyProblems || r.problem).map(({ name, resolved, states, modal, suggested }) => {
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
                  if (state === 'missing' || state === 'empty' || !resolved) {
                    const picked = !!pick && pick.value === null && columnOf(pick.chosenFrom) === source
                    return (
                      <Gap
                        key={source} state={state} column={source} picked={picked}
                        onPick={staging && (() => picked ? changeset.unstage(pick.id) : changeset.stage(change(name, emptyPick(source))))}
                      />
                    )
                  }
                  return (
                    <Cell
                      key={source} name={name} source={source} level={level} resolved={resolved} state={state} modal={modal}
                      // A split title staged from this source is not this cell's own value.
                      suggested={!!suggested && columnOf(suggested.source) === source}
                      picked={!!pick && columnOf(pick.chosenFrom) === source && resolved.values.some((v) =>
                        v.source === pick.chosenFrom && formatValue(v.value) === formatValue(pick.value))}
                      onPick={staging && ((value) => pick && columnOf(pick.chosenFrom) === source
                        ? changeset.unstage(pick.id)
                        : changeset.stage(change(name, value)))}
                      splitFor={name === 'title' ? (v) => splits.get(splitKey(v)) : undefined}
                      onSplitPick={stageDerived} isStaged={isStaged} tag={tag}
                      notes={name === 'asin' ? notesFor : undefined}
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

type GapProps = { state: CellState; column: ColumnName; picked: boolean; onPick?: () => void }

function Gap({ state, column, picked, onPick }: GapProps) {
  const classes = [state, isReference(column) && 'reference', onPick && 'pickable', picked && 'picked'].filter(Boolean).join(' ')
  return (
    <td
      className={classes}
      title={onPick ? (picked ? 'Staged as “no value”; click to undo' : `${gapTitle(state, column)}. Click if no value is correct`) : gapTitle(state, column)}
      onClick={onPick}
      onKeyDown={onPick && ((e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onPick() } })}
      tabIndex={onPick ? 0 : undefined}
      role={onPick ? 'button' : undefined}
      aria-pressed={onPick ? picked : undefined}
    >
      —
      {picked && <span className="tick" aria-hidden>✓</span>}
    </td>
  )
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
  suggested: boolean
  picked: boolean
  onPick?: (value: SourceValue) => void
  splitFor?: (value: SourceValue) => TitleSplit | undefined
  onSplitPick?: (field: string, from: SourceValue, value: string) => void
  isStaged: (field: string, value: string) => boolean
  tag: (value: SourceValue) => string | undefined
  notes?: (value: SourceValue) => AsinNote[]
}

function Cell({ name, source, level, resolved, state, modal, suggested, picked, onPick, splitFor, onSplitPick, isStaged, tag, notes }: CellProps) {
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
          {notes?.(v).map((n) => <span key={n.text} className={n.warning ? "badge" : "badge hint"} title={n.title}>{n.text}</span>)}
          <SplitHint value={v} split={splitFor?.(v)} onPick={onSplitPick} isStaged={isStaged} />
        </div>
      ))}
      {name === 'description' && columnOf(resolved.source) === source && resolved.licence && <div className="licence">{resolved.licence}</div>}
      {picked && <span className="tick" aria-hidden>✓</span>}
      {suggested && !picked && <span className="tick suggested" title="Suggested: most sources agree">✓</span>}
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
