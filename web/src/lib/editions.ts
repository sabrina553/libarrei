import type { components } from '../api/schema'
import { columnProvides } from '../components/capabilities'
import { compareKey, recordCheck, rowStates } from './cellStates'
import { languageRank } from './languages'
import { COLUMN_LABELS, COLUMN_SOURCES, columnOf, COLUMNS, formatValue } from './format'

export type MergedEdition = components['schemas']['MergedEdition']

// The fields an edition's grid shows, in order; issues are counted over the same rows.
export const EDITION_FIELDS = ['title', 'subtitle', 'edition_statement', 'contributors', 'isbn13', 'isbn10', 'asin',
  'identifiers', 'publisher',
  'release_date', 'pages', 'format', 'format_detail', 'duration_seconds', 'language', 'series', 'cover_url']

export const FILTERS = {
  all: { label: 'All', test: () => true },
  issues: { label: 'Any issue', test: (e: MergedEdition) => issueCount(e) > 0 },
  conflicts: { label: 'Conflicts', test: (e: MergedEdition) => editionIssues(e).conflicts.length > 0 },
  missing: { label: 'Missing from a source', test: (e: MergedEdition) => COLUMNS.some((c) => !COLUMN_SOURCES[c].some((s) => e.ids[s])) },
  duplicates: { label: 'Duplicates', test: (e: MergedEdition) => (e.duplicates ?? []).length > 0 },
  duplicateAsin: { label: 'Duplicate ASIN', test: (e: MergedEdition) => sharedIdentifiers(e).has('asin') || sharedIdentifiers(e).has('store_asin') },
  fuzzy: { label: 'Fuzzy matches', test: (e: MergedEdition) => e.match_reason === 'fuzzy' },
  sparse: { label: 'Sparse', test: (e: MergedEdition) => isSparse(e) },
} as const

// Kept in step with SPARSE in src/libarrei/quality.py.
export const SPARSE = 40

/** The weakest source record's completeness score, or null when none was scored. */
export function lowestQuality(edition: MergedEdition): number | null {
  const scores = Object.values(edition.quality ?? {})
  return scores.length ? Math.min(...scores) : null
}

export function isSparse(edition: MergedEdition): boolean {
  const lowest = lowestQuality(edition)
  return lowest !== null && lowest < SPARSE
}

export function bestQuality(edition: MergedEdition): number | null {
  const scores = Object.values(edition.quality ?? {})
  return scores.length ? Math.max(...scores) : null
}

type SortValue = string | number | null
const text = (name: string) => (e: MergedEdition): SortValue => {
  const value = e.fields[name]?.value
  return value === null || value === undefined || value === '' ? null : String(value)
}

// Sortable table columns; dates are ISO 8601, so they sort correctly as text.
export const SORT_COLUMNS = {
  isbn13: text('isbn13'),
  format: text('format'),
  language: text('language'),
  release_date: text('release_date'),
  publisher: text('publisher'),
  match: (e: MergedEdition): SortValue => e.match_reason ?? null,
  issues: (e: MergedEdition): SortValue => issueCount(e),
  quality: (e: MergedEdition): SortValue => lowestQuality(e),
} as const

export type SortColumn = keyof typeof SORT_COLUMNS
export type Sort = { column: SortColumn; descending: boolean } | null

// Gaps go last whichever way the column is sorted.
function compare(a: SortValue, b: SortValue, descending = false): number {
  if (a === null || b === null) return a === b ? 0 : a === null ? 1 : -1
  const order = typeof a === 'number' && typeof b === 'number' ? a - b : String(a).localeCompare(String(b))
  return descending ? -order : order
}

/**
 * The table's order: by the chosen column, or by default language, then the best
 * record's quality (fullest first), then release date.
 */
export function sortEditions(editions: MergedEdition[], sort: Sort, preferred: string[] = []): MergedEdition[] {
  const by = sort
    ? (a: MergedEdition, b: MergedEdition) => compare(SORT_COLUMNS[sort.column](a), SORT_COLUMNS[sort.column](b), sort.descending)
    : (a: MergedEdition, b: MergedEdition) =>
        compare(languageRank(a, preferred), languageRank(b, preferred))
        || compare(SORT_COLUMNS.language(a), SORT_COLUMNS.language(b))
        || compare(bestQuality(a), bestQuality(b), true)
        || compare(SORT_COLUMNS.release_date(a), SORT_COLUMNS.release_date(b))
  // toSorted is stable, so equal rows keep the API's order.
  return editions.toSorted(by)
}

/** A header click: ascending, then descending, then back to the default order. */
export function nextSort(current: Sort, column: SortColumn): Sort {
  if (current?.column !== column) return { column, descending: false }
  return current.descending ? null : { column, descending: true }
}

/** "possible stub of 9780593820247": the fuller edition this one probably duplicates. */
export function stubLabel(edition: MergedEdition, editions: MergedEdition[]): string | null {
  if (!edition.stub_of) return null
  const target = editionKey({ ...edition, ids: edition.stub_of })
  const full = editions.find((e) => editionKey(e) === target)
  const isbn = full?.fields.isbn13?.value
  const [source, ids] = Object.entries(edition.stub_of)[0] ?? []
  return `possible stub of ${isbn ? String(isbn) : `${source} ${ids?.[0] ?? ''}`.trim()}`
}

export type FilterName = keyof typeof FILTERS

export type Issues = {
  // Fields whose grid row has a differing or a missing cell, as the grid's "Only problems" shows them.
  conflicts: string[]
  missing: string[]
  // Record-level flags, one issue each.
  flags: string[]
}

// Sorting asks for the same edition's issues many times; editions are never mutated, so they are cached.
const issuesCache = new WeakMap<MergedEdition, Issues>()

export function editionIssues(edition: MergedEdition): Issues {
  const cached = issuesCache.get(edition)
  if (cached) return cached
  const hasRecord = recordCheck(edition.fields, edition.ids)
  const conflicts: string[] = []
  const missing: string[] = []
  for (const name of EDITION_FIELDS) {
    const { states } = rowStates(name, edition.fields[name]?.values ?? [], (c) => columnProvides('edition', c, name), hasRecord)
    const all = Object.values(states)
    if (all.includes('differs')) conflicts.push(name)
    if (all.includes('missing')) missing.push(name)
  }
  const flags = [
    duplicateLabel(edition),
    edition.stub_of && 'possible stub of a fuller edition',
    ...(edition.format_clash_isbns ?? []).map((isbn) => `ISBN ${isbn} shared by records with different format, publisher and year`),
    ...authorless(edition).map((record) => `${record} names no author`),
    isSparse(edition) && 'sparse record',
    edition.match_reason === 'fuzzy' && `fuzzy match (${edition.confidence})`,
    edition.match_reason === 'asin' && 'matched only by a catalogue ASIN',
  ].filter((f): f is string => !!f)
  const issues = { conflicts, missing, flags }
  issuesCache.set(edition, issues)
  return issues
}

type Person = { name: string; role?: string | null }

/** Records whose contributor list has people but no author, such as only an editor and illustrator. */
export function authorless(edition: MergedEdition): string[] {
  return (edition.fields.contributors?.values ?? [])
    .filter((v) => Array.isArray(v.value) && v.value.length > 0
      && !(v.value as Person[]).some((p) => (p.role ?? 'author') === 'author'))
    .map((v) => `${COLUMN_LABELS[columnOf(v.source)]} ${v.source_id}`)
}

export function issueCount(edition: MergedEdition): number {
  const { conflicts, missing, flags } = editionIssues(edition)
  return conflicts.length + missing.length + flags.length
}

/** The hover text behind the Issues count. */
export function issueSummary({ conflicts, missing, flags }: Issues): string {
  return [
    conflicts.length && `Conflicts: ${conflicts.join(', ')}`,
    missing.length && `Missing: ${missing.join(', ')}`,
    ...flags,
  ].filter(Boolean).join('\n')
}

function sharedIdentifiers(edition: MergedEdition): Set<string> {
  return new Set(Object.values(edition.duplicate_reasons ?? {}).flat())
}

/** "duplicate · ISBN" style badge text; ISBN-13 and ISBN-10 read as one kind to a librarian. */
export function duplicateLabel(edition: MergedEdition): string | null {
  if (!(edition.duplicates ?? []).length) return null
  const shared = sharedIdentifiers(edition)
  const kinds = [
    (shared.has('isbn13') || shared.has('isbn10')) && 'ISBN',
    // An ASIN the store itself reported is firm evidence; one only catalogues cite may be misattributed.
    shared.has('store_asin') ? 'ASIN (store confirmed)' : shared.has('asin') && 'ASIN',
  ].filter(Boolean)
  return ['duplicate', ...kinds].join(' · ')
}

/** A stable key from the source IDs, which don't change between fetches. */
export function editionKey(edition: MergedEdition): string {
  return Object.entries(edition.ids)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([source, ids]) => `${source}:${(ids ?? []).join('+')}`)
    .join('|')
}

export type Folded = { edition: MergedEdition; copies: MergedEdition[] }

/**
 * Tucks each likely copy (an identifier-less stub) under the edition it copies, when that edition
 * is listed too, so a handful of near-empty records does not bury the real one. Order is kept.
 */
export function foldCopies(editions: MergedEdition[]): Folded[] {
  const keys = new Set(editions.map(editionKey))
  const originalOf = (e: MergedEdition) => {
    if (!e.stub_of) return null
    const key = editionKey({ ...e, ids: e.stub_of })
    return keys.has(key) ? key : null
  }
  const copies = new Map<string, MergedEdition[]>()
  for (const e of editions) {
    const key = originalOf(e)
    if (key) copies.set(key, [...(copies.get(key) ?? []), e])
  }
  return editions.filter((e) => !originalOf(e)).map((edition) => ({ edition, copies: copies.get(editionKey(edition)) ?? [] }))
}

const DETAIL_FIELDS = ['pages', 'duration_seconds', 'contributors', 'publisher', 'release_date', 'cover_url', 'subtitle', 'edition_statement']

/** What a copy holds that its original lacks or states differently: worth copying over before it is merged away. */
export function copyExtras(copy: MergedEdition, original: MergedEdition): string[] {
  return DETAIL_FIELDS.flatMap((name) => {
    const mine = copy.fields[name]?.value
    if (mine === null || mine === undefined || mine === '') return []
    const theirs = original.fields[name]?.value
    if (theirs === null || theirs === undefined || theirs === '') return [`adds ${name.replaceAll('_', ' ')}`]
    if (compareKey(mine) === compareKey(theirs)) return []
    const shown = name === 'cover_url' ? '' : `: ${formatValue(mine)}`
    return [`differs on ${name.replaceAll('_', ' ')}${shown}`]
  })
}
