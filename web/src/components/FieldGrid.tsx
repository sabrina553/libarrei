import type { components } from '../api/schema'
import { buildChange, changeset, useChangeset } from '../lib/changeset'
import { formatValue, SOURCE_LABELS, SOURCES, type SourceName } from '../lib/format'
import { provides, type Level } from './capabilities'

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
                    picked={pick?.chosenFrom === source}
                    onPick={staging && ((value) => pick?.chosenFrom === source
                      ? changeset.unstage(pick.id)
                      : changeset.stage(buildChange(staging.book, staging.scope, name, value, resolved.values, staging.records)))}
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

type CellProps = {
  name: string
  source: SourceName
  resolved: Resolved
  picked: boolean
  onPick?: (value: Resolved['values'][number]) => void
}

function Cell({ name, source, resolved, picked, onPick }: CellProps) {
  const values = (resolved.values ?? []).filter((v) => v.source === source)
  if (!values.length) return <td className="empty" title="No value on this record">—</td>
  const chosen = resolved.source === source
  const classes = [chosen && 'chosen', picked && 'picked'].filter(Boolean).join(' ') || undefined
  return (
    <td className={classes} title={chosen ? 'Chosen value' : undefined}>
      {values.map((v, i) => (
        <div key={i} className={name === 'description' ? 'long' : undefined}>
          {name === 'cover_url' ? <img src={String(v.value)} alt="" loading="lazy" /> : formatValue(v.value)}
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
