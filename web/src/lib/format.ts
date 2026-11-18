// Field values arrive untyped (a title, a page count, a list of contributors…),
// so one function turns any of them into display text.
type Named = { name: string; role?: string; position?: string | null }
type Identifier = { scheme: string; value: string }

export function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (Array.isArray(value)) return value.map(formatValue).join(', ')
  if (typeof value === 'object') {
    const v = value as Named
    if ('scheme' in value) {
      const id = value as Identifier
      return `${id.scheme}: ${id.value}`
    }
    if ('position' in v) return v.position ? `${v.name} #${v.position}` : v.name
    if (v.role && v.role !== 'author') return `${v.name} (${v.role})`
    return v.name ?? JSON.stringify(value)
  }
  return String(value)
}

/** A length in seconds as h:mm, e.g. 37800 → "10:30". */
export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '—'
  const minutes = Math.round(seconds / 60)
  return `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, '0')}`
}

export const SOURCES = ['hardcover', 'goodreads', 'openlibrary', 'audible', 'amazon'] as const
export type SourceName = (typeof SOURCES)[number]

export const SOURCE_LABELS: Record<SourceName, string> = {
  hardcover: 'Hardcover',
  goodreads: 'Goodreads',
  openlibrary: 'Open Library',
  audible: 'Audible',
  amazon: 'Amazon',
}

// The grid's columns. Audible is Amazon's audiobook store, so both share one column
// while staying separate sources, so corrections still say which store to fix.
export const COLUMNS = ['hardcover', 'goodreads', 'openlibrary', 'amazon'] as const
export type ColumnName = (typeof COLUMNS)[number]

export const COLUMN_SOURCES: Record<ColumnName, readonly SourceName[]> = {
  hardcover: ['hardcover'],
  goodreads: ['goodreads'],
  openlibrary: ['openlibrary'],
  amazon: ['amazon', 'audible'],
}

export const COLUMN_LABELS: Record<ColumnName, string> = {
  hardcover: 'Hardcover',
  goodreads: 'Goodreads',
  openlibrary: 'Open Library',
  amazon: 'Amazon',
}

// Stores whose listings libarrei only reads for reference: their values vote and can be
// picked, but gaps in them are not flagged and no corrections are staged against them.
export const REFERENCE_SOURCES: ReadonlySet<SourceName> = new Set(['amazon', 'audible'])

export function isReference(column: ColumnName): boolean {
  return COLUMN_SOURCES[column].every((s) => REFERENCE_SOURCES.has(s))
}

// Short labels for compact badges such as "missing: HC, GR".
export const COLUMN_ABBREVIATIONS: Record<ColumnName, string> = {
  hardcover: 'HC',
  goodreads: 'GR',
  openlibrary: 'OL',
  amazon: 'AMZ',
}

export function columnOf(source: SourceName): ColumnName {
  return COLUMNS.find((c) => COLUMN_SOURCES[c].includes(source))!
}

/**
 * Which store a value in a shared column came from: Audible, or Amazon's Kindle or
 * print listing, judged from that record's format. Undefined in single-source columns.
 */
export function storeTag(source: SourceName, format: unknown): string | undefined {
  if (source === 'audible') return 'Audible'
  if (source !== 'amazon') return undefined
  if (format === 'ebook') return 'Kindle'
  if (format === 'physical') return 'Print'
  return undefined
}
