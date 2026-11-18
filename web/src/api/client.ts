import { amazonCookie, getToken } from '../settings/token'
import type { components } from './schema'

export type LookupResponse = components['schemas']['LookupResponse']
export type JobView = components['schemas']['JobView']
export type JobRequest = components['schemas']['JobRequest']

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = getToken()
  if (token) headers.set('X-Hardcover-Token', token)
  const cookie = amazonCookie.get()
  if (cookie) headers.set('X-Amazon-Cookie', cookie)
  if (init.body) headers.set('Content-Type', 'application/json')

  const response = await fetch(path, { ...init, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = typeof body.detail === 'string' ? body.detail : body.detail?.message
    throw new ApiError(response.status, detail ?? response.statusText)
  }
  return response.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string }>('/health'),
  lookup: (query: JobRequest) => request<LookupResponse>(`/v1/lookup?${params(query)}`),
  startJob: (query: JobRequest) => request<JobView>('/v1/jobs', { method: 'POST', body: JSON.stringify(query) }),
  job: (id: string) => request<JobView>(`/v1/jobs/${encodeURIComponent(id)}`),
}

function params(query: JobRequest): string {
  const entries = Object.entries(query).filter((pair): pair is [string, string] => Boolean(pair[1]))
  return new URLSearchParams(entries).toString()
}
