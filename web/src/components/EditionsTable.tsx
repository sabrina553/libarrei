import { Fragment, useState } from 'react'
import { EDITION_FIELDS, editionIssues, editionKey, FILTERS, issueSummary, isSparse, lowestQuality, nextSort, sortEditions, type FilterName, type MergedEdition, type Sort, type SortColumn } from '../lib/editions'
import { COLUMN_LABELS, COLUMN_SOURCES, COLUMNS, formatValue } from '../lib/format'
import { byLanguage } from '../lib/languages'
import { SlugsContext } from '../lib/links'
import { getLanguagePrefs } from '../settings/languages'
import { FieldGrid } from './FieldGrid'

// Rendering thousands of rows at once is slow; show a page and let the librarian ask for more.
const PAGE = 100
// Column headers; null marks one that cannot be sorted.
const HEADERS: [SortColumn | null, string][] = [
  ['isbn13', 'ISBN-13'], ['format', 'Format'], ['language', 'Language'], ['release_date', 'Released'],
  ['publisher', 'Publisher'], [null, 'Sources'], ['match', 'Match'], ['issues', 'Issues'], ['quality', 'Quality'],
]

const LANGUAGE_RULES = {
  off: 'Every language',
  preferred: 'Your preferred languages',
  'fallback-all': 'None in your preferred languages, so every language',
  'fallback-english': 'None in your preferred languages, so English',
  'fallback-none': 'None in your preferred languages',
} as const

export function EditionsTable({ editions, book }: { editions: MergedEdition[]; book: string }) {
  const [filter, setFilter] = useState<FilterName>('all')
  const [open, setOpen] = useState<string | null>(null)
  const [limit, setLimit] = useState(PAGE)
  const [sort, setSort] = useState<Sort>(null)
  const [allLanguages, setAllLanguages] = useState(false)
  const prefs = getLanguagePrefs()
  const view = byLanguage(editions, allLanguages ? { ...prefs, preferred: [] } : prefs)
  const inView = view.shown
  const shown = sortEditions(inView.filter(FILTERS[filter].test), sort, prefs.preferred)

  return (
    <section>
      <div className="filters" role="group" aria-label="Filter editions">
        {(Object.keys(FILTERS) as FilterName[]).map((name) => (
          <button key={name} className={name === filter ? 'active' : 'secondary'} onClick={() => { setFilter(name); setLimit(PAGE) }}>
            {FILTERS[name].label} ({inView.filter(FILTERS[name].test).length})
          </button>
        ))}
      </div>
      {(view.hidden > 0 || allLanguages) && (
        <p className="muted">
          {allLanguages ? 'Showing every language. ' : `${LANGUAGE_RULES[view.rule]}; ${view.hidden} other-language edition${view.hidden === 1 ? '' : 's'} hidden. `}
          <button type="button" className="link" onClick={() => setAllLanguages(!allLanguages)}>
            {allLanguages ? 'Use my language settings' : 'Show all languages'}
          </button>
        </p>
      )}
      <table className="editions">
        <thead>
          <tr>
            {HEADERS.map(([column, label]) => column === null ? <th key={label}>{label}</th> : (
              <th key={label} aria-sort={sort?.column === column ? (sort.descending ? 'descending' : 'ascending') : undefined}>
                <button type="button" className="sort" onClick={() => setSort(nextSort(sort, column))}
                  title="Sort by this column; click again to reverse, a third time for the default order">
                  {label}{sort?.column === column && (sort.descending ? ' ▼' : ' ▲')}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shown.slice(0, limit).map((edition) => {
            const key = editionKey(edition)
            const value = (name: string) => formatValue(edition.fields[name]?.value)
            const issues = editionIssues(edition)
            const issueTotal = issues.conflicts.length + issues.missing.length + issues.flags.length
            const lowest = lowestQuality(edition)
            return (
              <Fragment key={key}>
                <tr className="row" onClick={() => setOpen(open === key ? null : key)} aria-expanded={open === key}>
                  <td className="mono">{value('isbn13')}</td>
                  <td>{value('format')}</td>
                  <td>{value('language')}</td>
                  <td>{value('release_date')}</td>
                  <td>{value('publisher')}</td>
                  <td>
                    {COLUMNS.map((c) => (
                      <span key={c} className={COLUMN_SOURCES[c].some((s) => edition.ids[s]) ? 'src on' : 'src'} title={COLUMN_LABELS[c]}>{COLUMN_LABELS[c][0]}</span>
                    ))}
                  </td>
                  <td>{edition.match_reason === 'fuzzy' ? `fuzzy ${edition.confidence}` : edition.match_reason ?? '—'}</td>
                  <td title={issueSummary(issues) || undefined} className={issueTotal ? 'issues' : undefined}>{issueTotal || ''}</td>
                  <td className={isSparse(edition) ? 'quality low' : 'quality'} title="Completeness of the weakest source record">
                    {lowest === null ? '—' : `${lowest} %`}
                  </td>
                </tr>
                {open === key && (
                  <tr><td colSpan={9}><SlugsContext value={edition.slugs ?? {}}><FieldGrid fields={edition.fields} order={EDITION_FIELDS} level="edition" asinChecks={edition.asin_checks} asinStores={edition.asin_stores} quality={edition.quality} staging={{ book, scope: key, records: edition.ids }} /></SlugsContext></td></tr>
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
