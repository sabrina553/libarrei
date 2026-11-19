import { changeset, toMarkdown, useChangeset } from '../lib/changeset'
import { formatValue, SOURCE_LABELS } from '../lib/format'
import { merges, mergesToMarkdown, useMerges } from '../lib/merges'

export function Changes() {
  const changes = useChangeset()
  const { merges: staged, notDuplicates } = useMerges()
  const corrections = changes.reduce((n, c) => n + c.corrections.length, 0)
  const markdown = () => toMarkdown(changes) + (staged.length ? '\n' + mergesToMarkdown(staged) : '')

  if (!changes.length && !staged.length && !notDuplicates.length)
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
        {changes.length} pick{changes.length === 1 ? '' : 's'}, {corrections} correction{corrections === 1 ? '' : 's'} and {staged.length} merge{staged.length === 1 ? '' : 's'} to make.{' '}
        <button onClick={() => download('libarrei-changeset.md', markdown(), 'text/markdown')}>Export Markdown</button>{' '}
        <button className="secondary" onClick={() => download('libarrei-changeset.json', JSON.stringify({ changes, merges: staged }, null, 2), 'application/json')}>Export JSON</button>{' '}
        <button className="secondary" onClick={() => { if (confirm('Discard every staged change and merge?')) { changeset.clear(); merges.clear() } }}>Discard all</button>
      </p>
      {staged.length > 0 && (
        <>
          <h2>Merges</h2>
          <table className="editions">
            <thead><tr><th>Book</th><th>Duplicate</th><th>Merge into</th><th>Values kept</th><th></th></tr></thead>
            <tbody>
              {staged.map((m) => (
                <tr key={m.id}>
                  <td>{m.book}</td>
                  <td>{SOURCE_LABELS[m.source]} <span className="mono">{m.record}</span></td>
                  <td>{SOURCE_LABELS[m.into.source]} <span className="mono">{m.into.record}</span></td>
                  <td>{m.carried.join(', ') || <span className="muted">none</span>}</td>
                  <td><button className="secondary" onClick={() => merges.unstage(m.id)}>Undo</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      {notDuplicates.length > 0 && (
        <p className="muted">
          {notDuplicates.length} record{notDuplicates.length === 1 ? '' : 's'} marked as not a duplicate.{' '}
          <button className="link" onClick={() => notDuplicates.forEach(merges.forgetRejection)}>Suggest them again</button>
        </p>
      )}
      {changes.length > 0 && <h2>Field corrections</h2>}
      {changes.length > 0 && <table className="editions">
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
      </table>}
    </section>
  )
}

function download(name: string, text: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type }))
  const link = Object.assign(document.createElement('a'), { href: url, download: name })
  link.click()
  URL.revokeObjectURL(url)
}
