// A librarian's own credentials live only in this browser. They are sent to the
// libarrei API per request and never stored server-side.

export type Secret = { get: () => string | null; set: (value: string) => void; forget: () => void }

function secret(key: string): Secret {
  return {
    get() {
      try {
        return localStorage.getItem(key)
      } catch {
        // Storage can be blocked (private windows, strict settings); fall back to none.
        return null
      }
    },
    set(value) {
      try {
        localStorage.setItem(key, value.trim())
      } catch {
        // Nothing to do: the app still works with the server's own settings.
      }
    },
    forget() {
      try {
        localStorage.removeItem(key)
      } catch {
        // As above.
      }
    },
  }
}

export const hardcoverToken = secret('libarrei.hardcoverToken')
// Switches the Amazon source on for this browser's requests; off when unset.
export const amazonCookie = secret('libarrei.amazonCookie')

export const getToken = hardcoverToken.get
export const setToken = hardcoverToken.set
export const forgetToken = hardcoverToken.forget
