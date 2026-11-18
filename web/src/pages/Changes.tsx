import { changeset, toMarkdown, useChangeset } from '../lib/changeset'
import { formatValue, SOURCE_LABELS } from '../lib/format'

export function Changes() {
  const changes = useChangeset()
  const corrections = changes.reduce((n, c) => n + c.corrections.length, 0)

  if (!changes.length)
    return (
      <section>
        <h1>Changes</h1>
        <p className="muted">Nothing staged yet. On a book, choose “Use this” on the correct value for a field.</p>
      </section>
    )

  return (
    <section>
      <h1>Changes</h1>
      <p>
        {changes.length} pick{changes.length === 1 ? '' : 's'}, {corrections} correction{corrections === 1 ? '' : 's'} to make.{' '}
        <button onClick={() => download('libarrei-changeset.md', toMarkdown(changes), 'text/markdown')}>Export Markdown</button>{' '}
        <button className="secondary" onClick={() => download('libarrei-changeset.json', JSON.stringify(changes, null, 2), 'application/json')}>Export JSON</button>{' '}
        <button className="secondary" onClick={() => confirm('Discard every staged change?') && changeset.clear()}>Discard all</button>
      </p>
      <table className="editions">
        <thead><tr><th>Book</th><th>Field</th><th>Correct value</th><th>Fix in</th><th></th></tr></thead>
        <tbody>
          {changes.map((c) => (
            <tr key={c.id}>
              <td>{c.book}{c.scope !== 'work' && <span className="muted"> (edition)</span>}</td>
              <td>{c.field}</td>
              <td>{formatValue(c.value)} <span className="muted">from {SOURCE_LABELS[c.chosenFrom]}</span></td>
              <td>
                {c.corrections.length
                  ? c.corrections.map((x) => <div key={x.source + x.record}>{SOURCE_LABELS[x.source]} <span className="mono">{x.record}</span>: {formatValue(x.current)}</div>)
                  : <span className="muted">all sources already agree</span>}
              </td>
              <td><button className="secondary" onClick={() => changeset.unstage(c.id)}>Unstage</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function download(name: string, text: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type }))
  const link = Object.assign(document.createElement('a'), { href: url, download: name })
  link.click()
  URL.revokeObjectURL(url)
}
