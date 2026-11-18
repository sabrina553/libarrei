import { useSyncExternalStore } from 'react'
import { formatValue, REFERENCE_SOURCES, SOURCES, type SourceName } from './format'

/** One field on one source's record that should be changed to the staged value. */
export type Correction = { source: SourceName; record: string; current: unknown }

export type Change = {
  id: string
  book: string
  // "work" or an edition key; together with the field it identifies the pick.
  scope: string
  field: string
  value: unknown
  chosenFrom: SourceName
  corrections: Correction[]
}

type SourceValue = { value: unknown; source: SourceName; source_id: string }

/**
 * Picking a value stages a correction for every other source whose record
 * disagrees with it or lacks the field entirely. Reference-only stores are
 * never corrected, though their values can still be picked.
 */
export function buildChange(
  book: string, scope: string, field: string, pick: SourceValue,
  values: SourceValue[], records: Partial<Record<SourceName, string[]>>,
): Change {
  const wanted = formatValue(pick.value)
  const corrections: Correction[] = []
  for (const source of SOURCES) {
    if (source === pick.source || REFERENCE_SOURCES.has(source)) continue
    for (const record of records[source] ?? []) {
      const current = values.find((v) => v.source === source && v.source_id === record)
      if (!current || formatValue(current.value) !== wanted)
        corrections.push({ source, record, current: current?.value ?? null })
    }
  }
  return { id: `${scope}::${field}`, book, scope, field, value: pick.value, chosenFrom: pick.source, corrections }
}

// A tiny store kept in localStorage so staged work survives a reload.
const KEY = 'libarrei.changeset'
const listeners = new Set<() => void>()
let changes: Change[] = load()

function load(): Change[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '[]') as Change[]
  } catch {
    return []
  }
}

function save(next: Change[]): void {
  changes = next
  try {
    localStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    // Storage may be blocked; the changeset still works until the tab closes.
  }
  listeners.forEach((listener) => listener())
}

export const changeset = {
  stage: (change: Change) => save([...changes.filter((c) => c.id !== change.id), change]),
  unstage: (id: string) => save(changes.filter((c) => c.id !== id)),
  clear: () => save([]),
  all: () => changes,
}

export function useChangeset(): Change[] {
  return useSyncExternalStore(
    (listener) => { listeners.add(listener); return () => listeners.delete(listener) },
    changeset.all,
  )
}

export function toMarkdown(all: Change[]): string {
  const lines = ['# libarrei changeset', '']
  for (const source of SOURCES) {
    const items = all.flatMap((c) => c.corrections.filter((x) => x.source === source).map((x) => ({ c, x })))
    if (!items.length) continue
    lines.push(`## ${source}`, '')
    for (const { c, x } of items)
      lines.push(`- **${c.book}**, record \`${x.record}\`, ${c.field}: ${formatValue(x.current)} → ${formatValue(c.value)} (from ${c.chosenFrom})`)
    lines.push('')
  }
  return lines.join('\n')
}
