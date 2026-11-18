import type { components } from '../api/schema'

type Resolved = components['schemas']['Resolved']
type SourceValue = Resolved['values'][number]

// Where the split-off part belongs: a subtitle, or an edition statement such as "Deluxe Edition".
export type TitleSplit = { title: string; subtitle: string; field: 'subtitle' | 'edition_statement' }

const normalise = (text: unknown) => String(text ?? '').trim().toLowerCase()

// Only these words may qualify "edition", so a real subtitle such as "The Last Edition" stays a subtitle.
const QUALIFIERS = new Set(['deluxe', 'anniversary', "collector's", 'collectors', 'special', 'limited', 'illustrated',
  'revised', 'expanded', 'updated', 'annotated', 'abridged', 'unabridged', 'new', 'first', 'second', 'third',
  'definitive', 'gift', 'commemorative', 'complete', 'uncut', 'international', 'movie', 'tie-in', 'tv', 'media',
  'slipcase', 'hardcover', 'paperback', 'large', 'print', 'and', 'silver', 'golden', 'jubilee', "author's",
  "authors", 'preferred', 'text', 'ed.', 'ed'])
// Words that are an edition statement on their own.
const ALONE = new Set(['revised', 'unabridged', 'abridged', 'illustrated', 'annotated', 'expanded'])

/** "Deluxe Edition", "2nd ed.", "50th Anniversary Edition", "Collector's Edition", "Revised". */
export function isEditionStatement(text: string): boolean {
  const words = text.trim().toLowerCase().replaceAll('’', "'").split(/\s+/)
  if (words.length === 1) return ALONE.has(words[0])
  const last = words[words.length - 1]
  if (!['edition', 'ed.', 'ed', 'version'].includes(last)) return false
  return words.slice(0, -1).every((w) => QUALIFIERS.has(w) || /^\d+(st|nd|rd|th)?$/.test(w))
}

/**
 * Finds titles shaped "X: Y" where another source's title is X or any subtitle is Y,
 * which suggests the subtitle was folded into the title. A Y that reads as an edition
 * statement is offered as one, and needs no other source to back it.
 * Keyed by source and record id.
 */
export function titleSplits(fields: Record<string, Resolved | undefined>): Map<string, TitleSplit> {
  const titles = fields.title?.values ?? []
  const subtitles = new Set((fields.subtitle?.values ?? []).map((v) => normalise(v.value)))
  const splits = new Map<string, TitleSplit>()
  for (const candidate of titles) {
    const match = /^(.+?):\s+(.+)$/.exec(String(candidate.value ?? ''))
    if (!match) continue
    const [, title, subtitle] = match.map((part) => part.trim())
    const otherTitles = titles.filter((v) => v.source !== candidate.source).map((v) => normalise(v.value))
    const statement = isEditionStatement(subtitle)
    if (statement || otherTitles.includes(normalise(title)) || subtitles.has(normalise(subtitle)))
      splits.set(splitKey(candidate), { title, subtitle, field: statement ? 'edition_statement' : 'subtitle' })
  }
  return splits
}

export function splitKey(value: Pick<SourceValue, 'source' | 'source_id'>): string {
  return `${value.source}::${value.source_id}`
}
