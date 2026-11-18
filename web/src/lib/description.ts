import { diffArrays } from 'diff'
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

// Below this share of words in common, two blurbs are different texts and a word diff is noise.
export const CLOSE_VARIANT = 0.6

type Token = { key: string; start: number; end: number }

// Case and punctuation are ignored, so "Hobbit," and "hobbit" count as the same word.
function tokens(text: string): Token[] {
  return [...text.matchAll(/\S+/g)]
    .map((m) => ({ key: m[0].toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ''), start: m.index, end: m.index + m[0].length }))
    .filter((t) => t.key)
}

/** Dice coefficient on the two texts' word sets: 1 for the same words, 0 for none shared. */
export function similarity(a: string, b: string): number {
  const x = new Set(tokens(a).map((t) => t.key))
  const y = new Set(tokens(b).map((t) => t.key))
  if (!x.size && !y.size) return 1
  let shared = 0
  for (const w of x) if (y.has(w)) shared++
  return (2 * shared) / (x.size + y.size)
}

/**
 * The text each source is compared against: the one most sources agree on, or,
 * when no two agree, the one closest on average to all the others.
 */
export function baseline(texts: string[]): string | null {
  const all = texts.map(normalise)
  const counts = new Map<string, number>()
  for (const text of all) counts.set(text, (counts.get(text) ?? 0) + 1)
  let best: string | null = null
  let most = 1
  for (const [text, count] of counts) if (count > most) [best, most] = [text, count]
  if (best !== null || !all.length) return best
  const distinct = [...counts.keys()]
  const closeness = (t: string) => distinct.reduce((n, o) => (o === t ? n : n + similarity(t, o)), 0)
  return distinct.reduce((a, b) => (closeness(b) > closeness(a) ? b : a))
}

export type Comparison = { ranges: Range[]; distinct: boolean }

/**
 * How `text` compares with the baseline: a close variant has the words the
 * baseline lacks marked; a different blurb is flagged with nothing marked.
 */
export function compare(text: string, base: string | null): Comparison {
  if (base === null || normalise(text) === base) return { ranges: [], distinct: false }
  if (similarity(text, base) < CLOSE_VARIANT) return { ranges: [], distinct: true }
  return { ranges: changedRanges(text, base), distinct: false }
}

/** Where `text` has words the baseline lacks; shared words are never marked. */
export function changedRanges(text: string, base: string | null): Range[] {
  if (base === null || normalise(text) === base) return []
  const ours = tokens(text)
  const ranges: Range[] = []
  let at = 0
  // Diffing word keys, not raw text, keeps offsets tied to the text's own words.
  for (const part of diffArrays(tokens(base).map((t) => t.key), ours.map((t) => t.key))) {
    if (part.removed) continue
    const words = ours.slice(at, at + part.value.length)
    at += part.value.length
    if (part.added && words.length) ranges.push([words[0].start, words[words.length - 1].end])
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
