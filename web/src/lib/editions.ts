import type { components } from '../api/schema'
import { SOURCES } from './format'

export type MergedEdition = components['schemas']['MergedEdition']

export const FILTERS = {
  all: { label: 'All', test: () => true },
  conflicts: { label: 'Conflicts', test: (e: MergedEdition) => conflictCount(e) > 0 },
  missing: { label: 'Missing from a source', test: (e: MergedEdition) => Object.keys(e.ids).length < SOURCES.length },
  duplicates: { label: 'Duplicates', test: (e: MergedEdition) => (e.duplicates ?? []).length > 0 },
  fuzzy: { label: 'Fuzzy matches', test: (e: MergedEdition) => e.match_reason === 'fuzzy' },
} as const

export type FilterName = keyof typeof FILTERS

export function conflictCount(edition: MergedEdition): number {
  return Object.values(edition.fields).filter((f) => f.conflict).length
}

/** A stable key from the source IDs, which don't change between fetches. */
export function editionKey(edition: MergedEdition): string {
  return Object.entries(edition.ids)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([source, ids]) => `${source}:${(ids ?? []).join('+')}`)
    .join('|')
}
