import type { JobRequest } from '../api/client'

// The search lives in the URL so a result page can be bookmarked or shared.
export function queryFromParams(params: URLSearchParams): JobRequest | null {
  const query: JobRequest = {
    isbn: params.get('isbn') || null,
    title: params.get('title') || null,
    author: params.get('author') || null,
  }
  return query.isbn || query.title ? query : null
}

export function paramsFromQuery(query: JobRequest): string {
  const entries = Object.entries(query).filter((pair): pair is [string, string] => Boolean(pair[1]?.trim()))
  return new URLSearchParams(entries.map(([k, v]) => [k, v.trim()])).toString()
}
