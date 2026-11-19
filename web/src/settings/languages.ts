// Which edition languages a librarian wants to see, kept in this browser like the other settings.

export type Fallback = 'all' | 'english' | 'none'
export type LanguagePrefs = { preferred: string[]; fallback: Fallback }

const KEY = 'libarrei.languages'
// No preference means no filtering, so a first visit shows everything.
export const NO_PREFS: LanguagePrefs = { preferred: [], fallback: 'all' }

export function getLanguagePrefs(): LanguagePrefs {
  try {
    const stored = JSON.parse(localStorage.getItem(KEY) ?? 'null')
    if (stored && Array.isArray(stored.preferred) && ['all', 'english', 'none'].includes(stored.fallback))
      return { preferred: stored.preferred.filter((c: unknown) => typeof c === 'string'), fallback: stored.fallback }
  } catch {
    // Blocked storage or a damaged value: fall back to showing everything.
  }
  return NO_PREFS
}

export function setLanguagePrefs(prefs: LanguagePrefs): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(prefs))
  } catch {
    // The filter simply stays off.
  }
}
