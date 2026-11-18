import { columnOf, COLUMN_SOURCES, COLUMNS, formatValue, isReference, REFERENCE_SOURCES, type ColumnName, type SourceName } from './format'

/**
 * How one column's cell compares with the other columns in the same row.
 * Sources sharing a column (Amazon and Audible) count as one.
 * - agrees: holds the most common value (or is the only value)
 * - differs: holds a value, but not the most common one
 * - missing: holds nothing although another source has a value (never for reference-only stores)
 * - empty: holds nothing, and neither does any other source
 * - unsupported: this source never provides the field
 * - norecord: this source has no record at all here, so a gap says nothing about its data
 */
export type CellState = 'agrees' | 'differs' | 'missing' | 'empty' | 'unsupported' | 'norecord'

export type RowStates = {
  states: Record<ColumnName, CellState>
  // The value most sources hold, which differing cells are compared against.
  modal: string | null
  problem: boolean
}

type Value = { value: unknown; source: SourceName }

// Covers are different URLs for the same image, and sources legitimately carry different identifier schemes.
const NOT_COMPARED = new Set(['cover_url', 'identifiers'])

export function compareKey(value: unknown): string {
  return formatValue(value).replace(/\s+/g, ' ').trim().toLowerCase()
}

export function rowStates(
  field: string, values: Value[], provides: (column: ColumnName) => boolean,
  hasRecord: (column: ColumnName) => boolean = () => true,
): RowStates {
  const bySource = new Map<ColumnName, Set<string>>()
  for (const v of values) {
    if (v.value === null || v.value === undefined || v.value === '') continue
    const column = columnOf(v.source)
    if (!bySource.has(column)) bySource.set(column, new Set())
    bySource.get(column)!.add(compareKey(v.value))
  }
  const modal = NOT_COMPARED.has(field) ? null : mostCommon(bySource)
  const states = {} as Record<ColumnName, CellState>
  for (const source of COLUMNS) {
    const keys = bySource.get(source)
    if (!hasRecord(source) && !keys) states[source] = 'norecord'
    else if (!provides(source)) states[source] = 'unsupported'
    else if (!keys) states[source] = bySource.size && !isReference(source) ? 'missing' : 'empty'
    else if (NOT_COMPARED.has(field) || bySource.size < 2) states[source] = 'agrees'
    // Duplicate records that disagree among themselves are a problem even when one matches.
    else states[source] = modal !== null && keys.has(modal) && keys.size === 1 ? 'agrees' : 'differs'
  }
  const problem = Object.values(states).some((s) => s === 'differs' || s === 'missing')
  return { states, modal, problem }
}

// Counted once per source, so duplicate records cannot outvote the other sources. A tie means no majority.
function mostCommon(bySource: Map<ColumnName, Set<string>>): string | null {
  const counts = new Map<string, number>()
  for (const keys of bySource.values()) for (const k of keys) counts.set(k, (counts.get(k) ?? 0) + 1)
  const ranked = [...counts].sort((a, b) => b[1] - a[1])
  if (!ranked.length || (ranked.length > 1 && ranked[0][1] === ranked[1][1])) return null
  return ranked[0][0]
}

// Contributors agree when their authors do; narrators and translators vary by edition.
function suggestionKey(field: string, value: unknown): string {
  if (field !== 'contributors' || !Array.isArray(value)) return compareKey(value)
  return (value as { name: string; role?: string }[])
    .filter((p) => (p.role ?? 'author') === 'author')
    .map((p) => compareKey(p.name)).sort().join('|')
}

/**
 * The value most columns hold, as one source's value to pick, or null when there
 * is no clear majority. Each column votes once, reference stores included, and at
 * least two must agree. An editable source is credited over a reference store.
 */
export function suggestion<T extends Value>(field: string, values: T[], quality: Quality = {}): T | null {
  if (NOT_COMPARED.has(field)) return null
  const byColumn = new Map<ColumnName, Set<string>>()
  for (const v of values) {
    const key = v.value === null || v.value === undefined || v.value === '' ? '' : suggestionKey(field, v.value)
    if (!key) continue
    const column = columnOf(v.source)
    if (!byColumn.has(column)) byColumn.set(column, new Set())
    byColumn.get(column)!.add(key)
  }
  const top = mostCommon(byColumn)
  const agreed = top !== null && [...byColumn.values()].filter((keys) => keys.has(top)).length >= 2
  const chosen = agreed ? top : qualityTieBreak(byColumn, quality)
  if (chosen === null) return null
  const holders = values.filter((v) => v.value !== null && v.value !== undefined && v.value !== '' && suggestionKey(field, v.value) === chosen)
  return holders.find((v) => !REFERENCE_SOURCES.has(v.source)) ?? holders[0] ?? null
}

export type Quality = Partial<Record<SourceName, number>>
// How far ahead the fullest record must be before its value is offered without a majority.
export const QUALITY_GAP = 30

/** A column's completeness: its best source's record. */
export function columnQuality(column: ColumnName, quality: Quality): number | undefined {
  const scores = COLUMN_SOURCES[column].map((s) => quality[s]).filter((q): q is number => q !== undefined)
  return scores.length ? Math.max(...scores) : undefined
}

// Only without a majority: a fuller record breaks a tie, it never outvotes agreement.
function qualityTieBreak(byColumn: Map<ColumnName, Set<string>>, quality: Quality): string | null {
  const ranked = [...byColumn].map(([column, keys]) => ({ keys, score: columnQuality(column, quality) ?? 0 }))
    .sort((a, b) => b.score - a.score)
  const [best] = ranked
  if (!best || best.keys.size !== 1) return null
  const key = [...best.keys][0]
  const rival = ranked.find((r) => !r.keys.has(key))
  return rival && best.score - rival.score >= QUALITY_GAP ? key : null
}

/** Splits `text` into the part shared with `reference` at each end and the differing middle. */
export function inlineDiff(text: string, reference: string): [string, string, string] {
  const t = text.toLowerCase()
  const r = reference.toLowerCase()
  let start = 0
  while (start < t.length && start < r.length && t[start] === r[start]) start++
  let end = 0
  // A shared ending only lines up when the lengths match; "2020" against "2025-12-30" ending in 0 is chance.
  while (t.length === r.length && end < t.length - start && end < r.length - start && t[t.length - 1 - end] === r[r.length - 1 - end]) end++
  return [text.slice(0, start), text.slice(start, text.length - end), text.slice(text.length - end)]
}

/** Columns whose cell in this row is a real gap, for the row's compact "missing: HC, GR" badge. */
export function missingColumns(states: Record<ColumnName, CellState>): ColumnName[] {
  return COLUMNS.filter((c) => states[c] === 'missing')
}
