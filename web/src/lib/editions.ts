import type { components } from '../api/schema'
import { SOURCES } from './format'

export type MergedEdition = components['schemas']['MergedEdition']

export const FILTERS = {
  all: { label: 'All', test: () => true },
  conflicts: { label: 'Conflicts', test: (e: MergedEdition) => conflictCount(e) > 0 },
  missing: { label: 'Missing from a source', test: (e: MergedEdition) => Object.keys(e.ids).length < SOURCES.length },
  duplicates: { label: 'Duplicates', test: (e: MergedEdition) => (e.duplicates ?? []).length > 0 },
  duplicateAsin: { label: 'Duplicate ASIN', test: (e: MergedEdition) => sharedIdentifiers(e).has('asin') },
  fuzzy: { label: 'Fuzzy matches', test: (e: MergedEdition) => e.match_reason === 'fuzzy' },
} as const

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
  const kinds = [(shared.has('isbn13') || shared.has('isbn10')) && 'ISBN', shared.has('asin') && 'ASIN'].filter(Boolean)
  return ['duplicate', ...kinds].join(' · ')
}

/** A stable key from the source IDs, which don't change between fetches. */
export function editionKey(edition: MergedEdition): string {
  return Object.entries(edition.ids)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([source, ids]) => `${source}:${(ids ?? []).join('+')}`)
    .join('|')
}
