import { Fragment, useState } from 'react'
import { conflictCount, duplicateLabel, editionKey, FILTERS, type FilterName, type MergedEdition } from '../lib/editions'
import { formatValue, SOURCE_LABELS, SOURCES } from '../lib/format'
import { FieldGrid } from './FieldGrid'

// Rendering thousands of rows at once is slow; show a page and let the librarian ask for more.
const PAGE = 100
const EDITION_FIELDS = ['title', 'subtitle', 'edition_statement', 'contributors', 'isbn13', 'isbn10', 'asin',
  'identifiers', 'publisher',
  'release_date', 'pages', 'format', 'format_detail', 'duration_seconds', 'language', 'series', 'cover_url']

export function EditionsTable({ editions, book }: { editions: MergedEdition[]; book: string }) {
  const [filter, setFilter] = useState<FilterName>('all')
  const [open, setOpen] = useState<string | null>(null)
  const [limit, setLimit] = useState(PAGE)
  const shown = editions.filter(FILTERS[filter].test)

  return (
    <section>
      <div className="filters" role="group" aria-label="Filter editions">
        {(Object.keys(FILTERS) as FilterName[]).map((name) => (
          <button key={name} className={name === filter ? 'active' : 'secondary'} onClick={() => { setFilter(name); setLimit(PAGE) }}>
            {FILTERS[name].label} ({editions.filter(FILTERS[name].test).length})
          </button>
        ))}
      </div>
      <table className="editions">
        <thead>
          <tr><th>ISBN-13</th><th>Format</th><th>Language</th><th>Released</th><th>Publisher</th><th>Sources</th><th>Match</th><th>Conflicts</th></tr>
        </thead>
        <tbody>
          {shown.slice(0, limit).map((edition) => {
            const key = editionKey(edition)
            const value = (name: string) => formatValue(edition.fields[name]?.value)
            const conflicts = conflictCount(edition)
            return (
              <Fragment key={key}>
                <tr className="row" onClick={() => setOpen(open === key ? null : key)} aria-expanded={open === key}>
                  <td className="mono">{value('isbn13')}</td>
                  <td>{value('format')}</td>
                  <td>{value('language')}</td>
                  <td>{value('release_date')}</td>
                  <td>{value('publisher')}</td>
                  <td>
                    {SOURCES.map((s) => (
                      <span key={s} className={edition.ids[s] ? 'src on' : 'src'} title={SOURCE_LABELS[s]}>{SOURCE_LABELS[s][0]}</span>
                    ))}
                    {duplicateLabel(edition) && <span className="badge">{duplicateLabel(edition)}</span>}
                  </td>
                  <td>{edition.match_reason === 'fuzzy' ? `fuzzy ${edition.confidence}` : edition.match_reason ?? '—'}</td>
                  <td>{conflicts || ''}</td>
                </tr>
                {open === key && (
                  <tr><td colSpan={8}><FieldGrid fields={edition.fields} order={EDITION_FIELDS} level="edition" staging={{ book, scope: key, records: edition.ids }} /></td></tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
      </table>
      {shown.length > limit && <button className="secondary" onClick={() => setLimit(limit + PAGE)}>Show more ({shown.length - limit} left)</button>}
    </section>
  )
}
