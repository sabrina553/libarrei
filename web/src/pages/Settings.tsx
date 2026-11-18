import { useState, type ReactNode } from 'react'
import { amazonCookie, hardcoverToken, type Secret } from '../settings/token'

export function Settings() {
  return (
    <section>
      <h1>Settings</h1>
      <SecretSetting heading="Hardcover token" label="Token" secret={hardcoverToken}>
        Your token stays in this browser and is sent only to libarrei. Create one under Settings → API on
        hardcover.app. Without it, libarrei uses the server's token if it has one.
      </SecretSetting>
      <SecretSetting heading="Amazon cookie" label="Cookie" secret={amazonCookie}>
        Optional, and off unless set. Amazon has no book API, so libarrei reads its pages as you would, using the
        Cookie header from your signed-in browser session (DevTools → Network → any amazon request). It stays in
        this browser and is sent only to libarrei. Scraping may breach Amazon's terms; use it at your discretion.
      </SecretSetting>
    </section>
  )
}

type Props = { heading: string; label: string; secret: Secret; children: ReactNode }

function SecretSetting({ heading, label, secret, children }: Props) {
  const [saved, setSaved] = useState(secret.get() !== null)
  const [draft, setDraft] = useState('')
  return (
    <>
      <h2>{heading}</h2>
      <p className="muted">{children}</p>
      {saved ? (
        <p>
          {label} saved.{' '}
          <button onClick={() => { secret.forget(); setSaved(false) }}>Forget {label.toLowerCase()}</button>
        </p>
      ) : (
        <form onSubmit={(e) => { e.preventDefault(); if (draft.trim()) { secret.set(draft); setDraft(''); setSaved(true) } }}>
          <label>
            {label} <input type="password" value={draft} onChange={(e) => setDraft(e.target.value)} autoComplete="off" />
          </label>{' '}
          <button type="submit">Save</button>
        </form>
      )}
    </>
  )
}
