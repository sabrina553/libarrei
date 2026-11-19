import { useState, type ReactNode } from 'react'
import { getLanguagePrefs, setLanguagePrefs, type Fallback } from '../settings/languages'
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
      <LanguageSetting />
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

// Common edition languages by ISO 639-1 code; others can be typed in.
const COMMON = [['en', 'English'], ['es', 'Spanish'], ['fr', 'French'], ['de', 'German'], ['it', 'Italian'],
  ['pt', 'Portuguese'], ['nl', 'Dutch'], ['ja', 'Japanese'], ['zh', 'Chinese'], ['ru', 'Russian']] as const

const FALLBACKS: [Fallback, string][] = [['all', 'Show every language'], ['english', 'Show English'], ['none', 'Show nothing']]

function LanguageSetting() {
  const [prefs, setPrefs] = useState(getLanguagePrefs)
  const [other, setOther] = useState('')
  const save = (next: typeof prefs) => { setPrefs(next); setLanguagePrefs(next) }
  // Order matters: it is the sort order of the editions table, so new picks go last.
  const toggle = (code: string) => save({ ...prefs,
    preferred: prefs.preferred.includes(code) ? prefs.preferred.filter((c) => c !== code) : [...prefs.preferred, code] })
  const extra = prefs.preferred.filter((c) => !COMMON.some(([code]) => code === c))
  return (
    <>
      <h2>Edition languages</h2>
      <p className="muted">
        Only editions in these languages are listed, in the order picked; editions with no language recorded always
        show. Leave all unticked to see every language. Kept in this browser.
      </p>
      <fieldset>
        <legend>Preferred</legend>
        {[...COMMON, ...extra.map((c) => [c, c] as const)].map(([code, name]) => (
          <label key={code} className="check">
            <input type="checkbox" checked={prefs.preferred.includes(code)} onChange={() => toggle(code)} /> {name}
          </label>
        ))}
        <form onSubmit={(e) => {
          e.preventDefault()
          const code = other.trim().toLowerCase()
          if (/^[a-z]{2,3}$/.test(code) && !prefs.preferred.includes(code)) toggle(code)
          setOther('')
        }}>
          <label>Other (ISO code, such as "pl") <input value={other} onChange={(e) => setOther(e.target.value)} size={4} /></label>{' '}
          <button type="submit" className="secondary">Add</button>
        </form>
      </fieldset>
      <fieldset>
        <legend>When a book has no edition in these languages</legend>
        {FALLBACKS.map(([value, label]) => (
          <label key={value} className="check">
            <input type="radio" name="fallback" checked={prefs.fallback === value} onChange={() => save({ ...prefs, fallback: value })} /> {label}
          </label>
        ))}
      </fieldset>
    </>
  )
}
