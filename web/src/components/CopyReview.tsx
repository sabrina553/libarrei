import { buildChange, changeset, useChangeset } from '../lib/changeset'
import { copyExtras, describeExtra, editionKey, matchEvidence, type MergedEdition } from '../lib/editions'
import { formatValue, SOURCE_LABELS, type SourceName } from '../lib/format'
import { merges, recordId } from '../lib/merges'
import { RecordLink } from './RecordLink'

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
            {extras.length > 0 && (
              <ul>
                {extras.map((extra) => (
                  <li key={extra.field}>
                    {describeExtra(extra)}{' '}
                    {isKept(extra.field, own.source, extra.value)
                      ? <span className="muted">kept</span>
                      : <button type="button" className="link" onClick={() => keep(extra.field, extra.value)}>Keep this value</button>}
                  </li>
                ))}
              </ul>
            )}
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
