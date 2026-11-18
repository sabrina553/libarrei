import type { SourceName } from './format'

type Value = { value: unknown; source: SourceName; source_id: string }

export type AsinStatus = 'same_product' | 'other_product' | 'not_found'
export type AsinNote = { text: string; title: string; warning: boolean }

/** The edition's format when every source agrees on it, else null. */
export function editionFormat(formats: Value[]): string | null {
  const distinct = new Set(formats.map((v) => String(v.value)))
  return distinct.size === 1 ? [...distinct][0] : null
}

/**
 * The store's own ASIN for an edition it sells: Audible's for an audiobook, Amazon's
 * Kindle listing for an ebook. A store's id for its own product needs no second vote.
 */
export function storeAsin<T extends Value>(values: T[], format: string | null, recordFormat: (v: T) => unknown): T | null {
  if (format === 'audiobook') return values.find((v) => v.source === 'audible' && v.value) ?? null
  if (format === 'ebook') return values.find((v) => v.source === 'amazon' && v.value && recordFormat(v) === 'ebook') ?? null
  return null
}

function storeName(values: Value[]): string {
  return values.some((v) => v.source === 'audible') ? 'Audible' : 'Amazon'
}

/** What is known about one ASIN in the row: its store check, and whether it suits the format. */
export function asinNotes(asin: string, values: Value[], checks: Record<string, string>, format: string | null): AsinNote[] {
  const notes: AsinNote[] = []
  const store = storeName(values)
  const status = checks[asin] as AsinStatus | undefined
  if (status === 'same_product')
    notes.push({ text: 'also valid', title: `Another ${store} listing of the same product, such as a regional one`, warning: false })
  else if (status === 'not_found')
    notes.push({ text: `not found on ${store}`, title: `${store} has no product with this ASIN`, warning: true })
  else if (status === 'other_product')
    notes.push({ text: `other product on ${store}`, title: `On ${store} this ASIN is a different book`, warning: true })
  // Print books' ASINs are normally their ISBN-10; B0… ids are Kindle and Audible products.
  if (format === 'physical' && /^B0/i.test(asin))
    notes.push({ text: 'Kindle/Audible ID?', title: 'ASIN looks like a Kindle/Audible ID on a print edition', warning: true })
  return notes
}
