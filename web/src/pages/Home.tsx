import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function Home() {
  const health = useQuery({ queryKey: ['health'], queryFn: api.health })
  return (
    <section>
      <h1>libarrei</h1>
      <p className="muted">Compare book metadata across Goodreads, Hardcover and Open Library.</p>
      <p>
        API: {health.isPending ? 'checking…' : health.isError ? <span className="bad">unreachable</span> : <span className="good">connected</span>}
      </p>
    </section>
  )
}
