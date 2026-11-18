import type { SourceName } from '../lib/format'

export type Level = 'work' | 'edition'

// Which fields each source can ever fill, taken from src/libarrei/sources/*/mapping.py.
// Keep in step with those files: a field missing here shows as "not provided".
const CAPABILITIES: Record<Level, Record<SourceName, ReadonlySet<string>>> = {
  edition: {
    hardcover: new Set(['title', 'subtitle', 'contributors', 'isbn13', 'isbn10', 'publisher',
      'release_date', 'pages', 'format', 'language', 'cover_url']),
    goodreads: new Set(['title', 'subtitle', 'contributors', 'isbn13', 'isbn10', 'asin', 'publisher',
      'release_date', 'pages', 'format', 'language', 'cover_url']),
    openlibrary: new Set(['title', 'subtitle', 'contributors', 'isbn13', 'isbn10', 'publisher',
      'release_date', 'pages', 'format', 'language', 'cover_url', 'series']),
  },
  work: {
    hardcover: new Set(['title', 'subtitle', 'contributors', 'description', 'series', 'genres',
      'original_release_date']),
    goodreads: new Set(['title', 'contributors', 'description', 'series', 'genres', 'original_release_date']),
    openlibrary: new Set(['title', 'subtitle', 'contributors', 'description', 'series', 'genres',
      'original_release_date']),
  },
}

export function provides(level: Level, source: SourceName, field: string): boolean {
  return CAPABILITIES[level][source].has(field)
}
