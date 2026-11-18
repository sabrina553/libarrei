import type { components } from '../api/schema'

type Resolved = components['schemas']['Resolved']
type SourceValue = Resolved['values'][number]

export type TitleSplit = { title: string; subtitle: string }

const normalise = (text: unknown) => String(text ?? '').trim().toLowerCase()

/**
 * Finds titles shaped "X: Y" where another source's title is X or any subtitle is Y,
 * which suggests the subtitle was folded into the title. Keyed by source and record id.
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
    if (otherTitles.includes(normalise(title)) || subtitles.has(normalise(subtitle)))
      splits.set(splitKey(candidate), { title, subtitle })
  }
  return splits
}

export function splitKey(value: Pick<SourceValue, 'source' | 'source_id'>): string {
  return `${value.source}::${value.source_id}`
}
