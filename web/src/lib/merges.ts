import { useSyncExternalStore } from 'react'
import type { SourceName } from './format'

/**
 * A librarian's verdict that one record copies another and should be merged into it on the
 * source. libarrei never writes to sources, so this is an instruction to carry out there.
 */
export type Merge = {
  id: string
  book: string
  source: SourceName
  record: string
  // The best version's record on the same source, or on whichever source has one.
  into: { source: SourceName; record: string }
  // Fields whose value from the copy was kept by staging it on the best version.
  carried: string[]
}

type State = { merges: Merge[]; notDuplicates: string[] }

const KEY = 'libarrei.merges'
const listeners = new Set<() => void>()
let state: State = load()

function load(): State {
  try {
    const stored = JSON.parse(localStorage.getItem(KEY) ?? 'null')
    if (stored && Array.isArray(stored.merges) && Array.isArray(stored.notDuplicates)) return stored
  } catch {
    // A damaged or blocked store starts empty.
  }
  return { merges: [], notDuplicates: [] }
}

function save(next: State): void {
  state = next
  try {
    localStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    // Storage may be blocked; decisions still hold until the tab closes.
  }
  listeners.forEach((listener) => listener())
}

export const recordId = (source: SourceName, record: string) => `${source}:${record}`

export const merges = {
  stage: (merge: Merge) => save({ ...state, merges: [...state.merges.filter((m) => m.id !== merge.id), merge] }),
  unstage: (id: string) => save({ ...state, merges: state.merges.filter((m) => m.id !== id) }),
  rejectCopy: (id: string) => save({ ...state, notDuplicates: [...new Set([...state.notDuplicates, id])] }),
  forgetRejection: (id: string) => save({ ...state, notDuplicates: state.notDuplicates.filter((n) => n !== id) }),
  clear: () => save({ merges: [], notDuplicates: [] }),
  all: () => state,
}

export function useMerges(): State {
  return useSyncExternalStore(
    (listener) => { listeners.add(listener); return () => listeners.delete(listener) },
    merges.all,
  )
}

export function mergesToMarkdown(all: Merge[]): string {
  if (!all.length) return ''
  const lines = ['## Merges', '']
  for (const m of all) {
    const kept = m.carried.length ? `; keep its ${m.carried.join(', ')}` : ''
    lines.push(`- **${m.book}**: merge ${m.source} \`${m.record}\` into ${m.into.source} \`${m.into.record}\`${kept}`)
  }
  return lines.join('\n') + '\n'
}
