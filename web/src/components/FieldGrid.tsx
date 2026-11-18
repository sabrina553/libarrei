import type { components } from '../api/schema'
import { buildChange, changeset, useChangeset } from '../lib/changeset'
import { formatValue, SOURCE_LABELS, SOURCES, type SourceName } from '../lib/format'
import { provides, type Level } from './capabilities'
import { splitKey, titleSplits, type TitleSplit } from './titleSplit'

export type Resolved = components['schemas']['Resolved']

const LABELS: Record<string, string> = {
  original_release_date: 'First published',
  release_date: 'Release date',
  cover_url: 'Cover',
  isbn13: 'ISBN-13',
  isbn10: 'ISBN-10',
  asin: 'ASIN',
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
  return (
    <table className="grid">
      <thead>
        <tr>
          <th>Field</th>
          {SOURCES.map((s) => <th key={s}>{SOURCE_LABELS[s]}</th>)}
        </tr>
      </thead>
      <tbody>
        {order.map((name) => {
          const resolved = fields[name]
          return (
            <tr key={name} className={resolved?.conflict ? 'conflict' : undefined}>
              <th scope="row">
                {fieldLabel(name)}
                {resolved?.conflict && <span className="badge" title="Sources disagree">conflict</span>}
              </th>
              {SOURCES.map((source) => {
                const id = staging && `${staging.scope}::${name}`
                const pick = staged.find((c) => c.id === id)
                if (!provides(level, source, name))
                  return <td key={source} className="unsupported" title={`${SOURCE_LABELS[source]} does not provide this field`}>not provided</td>
                if (!resolved) return <td key={source} className="empty" title="No value on this record">—</td>
                return (
                  <Cell
                    key={source} name={name} source={source} resolved={resolved}
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
  )
}

type SourceValue = Resolved['values'][number]

type CellProps = {
  name: string
  source: SourceName
  resolved: Resolved
  picked: boolean
  onPick?: (value: SourceValue) => void
  splitFor?: (value: SourceValue) => TitleSplit | undefined
  onSplitPick?: (field: string, from: SourceValue, value: string) => void
  isStaged: (field: string, value: string) => boolean
}

function Cell({ name, source, resolved, picked, onPick, splitFor, onSplitPick, isStaged }: CellProps) {
  const values = (resolved.values ?? []).filter((v) => v.source === source)
  if (!values.length) return <td className="empty" title="No value on this record">—</td>
  const chosen = resolved.source === source
  const classes = [chosen && 'chosen', picked && 'picked'].filter(Boolean).join(' ') || undefined
  return (
    <td className={classes} title={chosen ? 'Chosen value' : undefined}>
      {values.map((v, i) => (
        <div key={i} className={name === 'description' ? 'long' : undefined}>
          {name === 'cover_url' ? <img src={String(v.value)} alt="" loading="lazy" /> : formatValue(v.value)}
          <SplitHint value={v} split={splitFor?.(v)} onPick={onSplitPick} isStaged={isStaged} />
        </div>
      ))}
      {name === 'description' && chosen && resolved.licence && <div className="licence">{resolved.licence}</div>}
      {onPick && (
        <button className="pick" onClick={() => onPick(values[0])} aria-pressed={picked}>
          {picked ? 'Staged ✓' : 'Use this'}
        </button>
      )}
    </td>
  )
}

type SplitHintProps = {
  value: SourceValue
  split?: TitleSplit
  onPick?: (field: string, from: SourceValue, value: string) => void
  isStaged: (field: string, value: string) => boolean
}

function SplitHint({ value, split, onPick, isStaged }: SplitHintProps) {
  if (!split) return null
  const options = [['title', split.title], ['subtitle', split.subtitle]] as const
  return (
    <>
      <span className="badge hint" title="Another source's title or subtitle suggests this title includes the subtitle">
        subtitle may be in title
      </span>
      {onPick && options.map(([field, text]) => (
        <button key={field} className="pick" onClick={() => onPick(field, value, text)} aria-pressed={isStaged(field, text)}>
          {isStaged(field, text) ? 'Staged ✓' : `Use “${text}” as ${field}`}
        </button>
      ))}
    </>
  )
}
