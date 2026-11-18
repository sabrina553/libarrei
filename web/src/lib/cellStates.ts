import { formatValue, SOURCES, type SourceName } from './format'

/**
 * How one source's cell compares with the other sources in the same row.
 * - agrees: holds the most common value (or is the only value)
 * - differs: holds a value, but not the most common one
 * - missing: holds nothing although another source has a value
 * - empty: holds nothing, and neither does any other source
 * - unsupported: this source never provides the field
 */
export type CellState = 'agrees' | 'differs' | 'missing' | 'empty' | 'unsupported'

export type RowStates = {
  states: Record<SourceName, CellState>
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

export function rowStates(field: string, values: Value[], provides: (source: SourceName) => boolean): RowStates {
  const bySource = new Map<SourceName, Set<string>>()
  for (const v of values) {
    if (v.value === null || v.value === undefined || v.value === '') continue
    if (!bySource.has(v.source)) bySource.set(v.source, new Set())
    bySource.get(v.source)!.add(compareKey(v.value))
  }
  const modal = NOT_COMPARED.has(field) ? null : mostCommon(bySource)
  const states = {} as Record<SourceName, CellState>
  for (const source of SOURCES) {
    const keys = bySource.get(source)
    if (!provides(source)) states[source] = 'unsupported'
    else if (!keys) states[source] = bySource.size ? 'missing' : 'empty'
    else if (NOT_COMPARED.has(field) || bySource.size < 2) states[source] = 'agrees'
    // Duplicate records that disagree among themselves are a problem even when one matches.
    else states[source] = modal !== null && keys.has(modal) && keys.size === 1 ? 'agrees' : 'differs'
  }
  const problem = Object.values(states).some((s) => s === 'differs' || s === 'missing')
  return { states, modal, problem }
}

// Counted once per source, so duplicate records cannot outvote the other sources. A tie means no majority.
function mostCommon(bySource: Map<SourceName, Set<string>>): string | null {
  const counts = new Map<string, number>()
  for (const keys of bySource.values()) for (const k of keys) counts.set(k, (counts.get(k) ?? 0) + 1)
  const ranked = [...counts].sort((a, b) => b[1] - a[1])
  if (!ranked.length || (ranked.length > 1 && ranked[0][1] === ranked[1][1])) return null
  return ranked[0][0]
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
