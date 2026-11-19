import { buildChange, changeset, useChangeset } from '../lib/changeset'
import { compareCopy, copyExtras, editionKey, matchEvidence, type MergedEdition } from '../lib/editions'
import { formatValue, SOURCE_LABELS, type SourceName } from '../lib/format'
import { merges, recordId } from '../lib/merges'
import { fieldLabel } from './FieldGrid'
import { RecordLink } from './RecordLink'

// Covers are long URLs; a thumbnail compares at a glance.
function shown(field: string, value: unknown) {
  if (value === null || value === undefined || value === '') return <span className="muted">—</span>
  return field === 'cover_url' ? <img src={String(value)} alt="" height={60} /> : formatValue(value)
}

type Props = { book: string; best: MergedEdition; copies: MergedEdition[] }

/** The first record of an edition: a copy is one source's record, so this is the copy itself. */
export function firstRecord(edition: MergedEdition): { source: SourceName; record: string } | null {
  for (const [source, ids] of Object.entries(edition.ids)) if (ids?.length) return { source: source as SourceName, record: ids[0] }
  return null
}

/**
 * Possible duplicates of the best version, each with why it matched and what it would lose,
 * for a librarian to merge or dismiss. Merging is staged, to be carried out on the source.
 */
export function CopyReview({ book, best, copies }: Props) {
  const staged = useChangeset()
  const bestKey = editionKey(best)
  const target = (source: SourceName) => {
    const same = best.ids[source]?.[0]
    return same ? { source, record: same } : firstRecord(best)
  }
  const isKept = (field: string, source: SourceName, value: unknown) =>
    staged.some((c) => c.id === `${bestKey}::${field}` && c.chosenFrom === source && formatValue(c.value) === formatValue(value))

  return (
    <div className="copy-review">
      <p className="legend">
        <span style={{ background: 'var(--same-bg)' }}>same</span>
        <span style={{ background: 'var(--differs-bg)' }}>differs</span>
        <span style={{ background: 'var(--dup-bg)', outline: '1px solid var(--dup-edge)' }}>only on the duplicate</span>
        <span className="why">match key</span> fields are why the record was suspected
      </p>
      <p className="muted">
        Possible duplicates: records with no identifier that match this edition. Merge one into this version once
        you agree, keeping anything worth saving first; the merge is staged for you to carry out on the source.
      </p>
      {copies.map((copy) => {
        const own = firstRecord(copy)
        const into = own && target(own.source)
        if (!own || !into) return null
        const extras = copyExtras(copy, best)
        const evidence = matchEvidence(copy, best)
        const keep = (field: string, value: unknown) => {
          const values = best.fields[field]?.values ?? []
          changeset.stage(buildChange(book, bestKey, field, { value, source: own.source, source_id: own.record }, values, best.ids))
        }
        return (
          <div key={editionKey(copy)} className="copy-card">
            <div>
              <strong>{SOURCE_LABELS[own.source]}</strong>{' '}
              <RecordLink level="edition" value={{ source: own.source, source_id: own.record }} />
              {' '}<span className="muted">matches on {evidence.join(', ') || 'title, format and language'}</span>
            </div>
            <table className="compare">
              <thead><tr><th>Field</th><th>This version</th><th>Possible duplicate</th><th></th></tr></thead>
              <tbody>
                {compareCopy(copy, best).map((r) => (
                  <tr key={r.field} className={r.state}>
                    <th scope="row">{fieldLabel(r.field)}{r.why && <div className="why" title="Part of why this record was matched">match key</div>}</th>
                    <td>{shown(r.field, r.theirs)}</td>
                    <td className="mine">{shown(r.field, r.mine)}</td>
                    <td>
                      {(r.state === 'differs' || r.state === 'adds') && (isKept(r.field, own.source, r.mine)
                        ? <span className="muted">kept</span>
                        : <button type="button" className="link" onClick={() => keep(r.field, r.mine)}>Keep this value</button>)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="copy-actions">
              <button type="button" onClick={() => merges.stage({
                id: recordId(own.source, own.record), book, source: own.source, record: own.record, into,
                carried: extras.filter((e) => isKept(e.field, own.source, e.value)).map((e) => e.field),
              })}>Merge into this version</button>{' '}
              <button type="button" className="secondary" onClick={() => merges.rejectCopy(recordId(own.source, own.record))}>
                Not a duplicate
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
