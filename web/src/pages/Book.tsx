import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { api, type LookupResponse } from '../api/client'
import { EditionsTable } from '../components/EditionsTable'
import { FieldGrid } from '../components/FieldGrid'
import { formatValue } from '../lib/format'
import { queryFromParams } from '../lib/query'

// How often to ask whether a background fetch has finished.
const POLL_MS = 2000

const WORK_FIELDS = ['title', 'subtitle', 'contributors', 'series', 'original_release_date', 'genres', 'description']

export function Book() {
  const [params] = useSearchParams()
  const query = queryFromParams(params)
  const [jobId, setJobId] = useState<string | null>(null)

  const quick = useQuery({
    queryKey: ['lookup', query],
    queryFn: () => api.lookup(query!),
    enabled: query !== null,
  })
  const start = useMutation({ mutationFn: () => api.startJob(query!), onSuccess: (job) => setJobId(job.id) })
  const job = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => api.job(jobId!),
    enabled: jobId !== null,
    // Keep polling only while the job is unfinished.
    refetchInterval: (q) => (['queued', 'running'].includes(q.state.data?.status ?? 'queued') ? POLL_MS : false),
  })

  if (!query) return <p>No search given. <Link to="/">Search</Link></p>
  if (quick.isPending) return <p className="muted">Looking up…</p>
  if (quick.isError) return <p className="bad">{quick.error.message}</p>

  const full = job.data?.status === 'done' ? job.data.result : null
  const shown: LookupResponse = full ?? quick.data

  return (
    <section>
      <h1>{formatValue(shown.work.fields.title?.value)}</h1>
      <p className="muted">{formatValue(shown.work.fields.contributors?.value)}</p>
      <Notes notes={shown.notes} />
      <FieldGrid fields={shown.work.fields} order={WORK_FIELDS} />
      <p>
        {shown.work.editions.length} edition{shown.work.editions.length === 1 ? '' : 's'}{' '}
        {full ? '(every edition)' : '(matched editions only)'}
      </p>
      {!full && (
        <p>
          <button onClick={() => start.mutate()} disabled={jobId !== null && job.data?.status !== 'failed'}>
            Fetch every edition
          </button>{' '}
          <JobStatus status={job.data?.status} error={job.data?.error ?? start.error?.message} />
        </p>
      )}
      <EditionsTable editions={shown.work.editions} />
    </section>
  )
}

function Notes({ notes }: { notes?: Record<string, string> }) {
  const entries = Object.entries(notes ?? {})
  if (!entries.length) return null
  return (
    <ul className="notes">
      {entries.map(([source, note]) => <li key={source}>{source}: {note}</li>)}
    </ul>
  )
}

function JobStatus({ status, error }: { status?: string; error?: string | null }) {
  if (error) return <span className="bad">{error}</span>
  if (status === 'queued' || status === 'running')
    return <span className="muted">Fetching every edition… this can take a few minutes the first time.</span>
  return null
}
