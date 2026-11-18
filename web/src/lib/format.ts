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

export const SOURCES = ['hardcover', 'goodreads', 'openlibrary'] as const
export type SourceName = (typeof SOURCES)[number]

export const SOURCE_LABELS: Record<SourceName, string> = {
  hardcover: 'Hardcover',
  goodreads: 'Goodreads',
  openlibrary: 'Open Library',
}
