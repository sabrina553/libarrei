import { createContext } from 'react'
import type { Level } from '../components/capabilities'
import type { SourceName } from './format'

/** Slugs for sources whose pages are addressed by slug, as the API sends them. */
export type Slugs = Partial<Record<SourceName, string>>

/** The slugs of the work or edition being shown, so record links deep in a grid can reach them. */
export const SlugsContext = createContext<Slugs>({})

/** The source's own web page for a record, when it can be built from what we hold. */
export function recordUrl(level: Level, source: SourceName, id: string, slugs: Slugs = {}): string | undefined {
  const path = encodeURIComponent(id)
  if (source === 'openlibrary') return `https://openlibrary.org/${level === 'work' ? 'works' : 'books'}/${path}`
  if (source === 'goodreads') return `https://www.goodreads.com/${level === 'work' ? 'work/editions' : 'book/show'}/${path}`
  // The stores' domains come from the record, since each region has its own pages.
  if (source === 'audible') return slugs.audible ? `https://www.audible.${slugs.audible}/pd/${path}` : undefined
  if (source === 'amazon') return slugs.amazon ? `https://www.amazon.${slugs.amazon}/dp/${path}` : undefined
  // Hardcover pages hang off the book's slug, never its numeric id.
  const slug = slugs.hardcover
  if (!slug) return undefined
  const book = `https://hardcover.app/books/${encodeURIComponent(slug)}`
  return level === 'work' ? book : `${book}/editions/${path}`
}
