import type { components } from '../api/schema'
import { COLUMN_SOURCES, COLUMNS } from './format'

export type MergedEdition = components['schemas']['MergedEdition']

export const FILTERS = {
  all: { label: 'All', test: () => true },
  conflicts: { label: 'Conflicts', test: (e: MergedEdition) => conflictCount(e) > 0 },
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

export function conflictCount(edition: MergedEdition): number {
  return Object.values(edition.fields).filter((f) => f.conflict).length
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
