import { diffWords } from 'diff'
import type { components } from '../api/schema'

export type Block = components['schemas']['Block']
export type Run = components['schemas']['Run']
/** [start, end) character offsets into a description's flat text. */
export type Range = [number, number]

export function normalise(text: string): string {
  return text.replace(/\s+/g, ' ').trim()
}

/** Older responses carry only plain text, so rebuild paragraphs from blank lines. */
export function blocksOf(formatted: Block[] | null | undefined, text: string): Block[] {
  if (formatted?.length) return formatted
  return text.split(/\n\s*\n/).filter((p) => p.trim())
    .map((p) => ({ kind: 'paragraph', runs: [{ text: p.trim(), bold: false, italic: false }] }))
}

/** Runs joined, one character between blocks; highlight offsets index into this. */
export function flatText(blocks: Block[]): string {
  return blocks.map((b) => b.runs.map((r) => r.text).join('')).join('\n')
}

/**
 * The text each source is compared against: the one most sources agree on,
 * or the first source's when no two agree.
 */
export function baseline(texts: string[]): string | null {
  const counts = new Map<string, number>()
  for (const text of texts.map(normalise)) counts.set(text, (counts.get(text) ?? 0) + 1)
  let best: string | null = null
  let most = 1
  for (const [text, count] of counts) if (count > most) [best, most] = [text, count]
  return best ?? (texts.length ? normalise(texts[0]) : null)
}

/** Where `text` has words the baseline lacks; empty when they read the same. */
export function changedRanges(text: string, base: string | null): Range[] {
  if (base === null || normalise(text) === base) return []
  const ranges: Range[] = []
  let at = 0
  for (const part of diffWords(base, text)) {
    if (part.removed) continue
    const start = text.indexOf(part.value.trim() || part.value, at)
    // The diff's whitespace may not match the text's exactly; give up rather than mark the wrong words.
    if (start < 0) return []
    const end = start + (part.value.trim() || part.value).length
    if (part.added && part.value.trim()) ranges.push([start, end])
    at = end
  }
  return ranges
}

/** Cuts a run's text, which starts at `start` in the flat text, where highlighted ranges begin and end. */
export function splitByRanges(text: string, start: number, ranges: Range[]): [string, boolean][] {
  const end = start + text.length
  const cuts = new Set([start, end])
  for (const [a, b] of ranges) for (const c of [a, b]) if (c > start && c < end) cuts.add(c)
  const sorted = [...cuts].sort((a, b) => a - b)
  return sorted.slice(0, -1).map((a, i) => {
    const b = sorted[i + 1]
    return [text.slice(a - start, b - start), ranges.some(([x, y]) => x < b && y > a)]
  })
}
