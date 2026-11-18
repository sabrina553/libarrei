// The librarian's Hardcover token lives only in this browser. It is sent to the
// libarrei API per request and never stored server-side.
const KEY = 'libarrei.hardcoverToken'

export function getToken(): string | null {
  try {
    return localStorage.getItem(KEY)
  } catch {
    // Storage can be blocked (private windows, strict settings); fall back to none.
    return null
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(KEY, token.trim())
  } catch {
    // Nothing to do: the app still works with the server's own token.
  }
}

export function forgetToken(): void {
  try {
    localStorage.removeItem(KEY)
  } catch {
    // As above.
  }
}
