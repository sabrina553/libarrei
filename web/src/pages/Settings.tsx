import { useState } from 'react'
import { forgetToken, getToken, setToken } from '../settings/token'

export function Settings() {
  const [saved, setSaved] = useState(getToken() !== null)
  const [draft, setDraft] = useState('')

  return (
    <section>
      <h1>Settings</h1>
      <h2>Hardcover token</h2>
      <p className="muted">
        Your token stays in this browser and is sent only to libarrei. Create one under Settings → API on
        hardcover.app. Without it, libarrei uses the server's token if it has one.
      </p>
      {saved ? (
        <p>
          A token is saved.{' '}
          <button onClick={() => { forgetToken(); setSaved(false) }}>Forget token</button>
        </p>
      ) : (
        <form onSubmit={(e) => { e.preventDefault(); if (draft.trim()) { setToken(draft); setDraft(''); setSaved(true) } }}>
          <label>
            Token <input type="password" value={draft} onChange={(e) => setDraft(e.target.value)} autoComplete="off" />
          </label>{' '}
          <button type="submit">Save</button>
        </form>
      )}
    </section>
  )
}
