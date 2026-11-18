import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router'
import { Book } from './pages/Book'
import { Changes } from './pages/Changes'
import { useChangeset } from './lib/changeset'
import { Search } from './pages/Search'
import { Settings } from './pages/Settings'

const queryClient = new QueryClient({
  // Lookups are cached server-side already; refetching on every window focus would just repeat them.
  defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <header>
          <nav>
            <NavLink to="/" end>Search</NavLink>
            <ChangesLink />
            <NavLink to="/settings">Settings</NavLink>
          </nav>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Search />} />
            <Route path="/book" element={<Book />} />
            <Route path="/changes" element={<Changes />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

function ChangesLink() {
  const count = useChangeset().length
  return <NavLink to="/changes">Changes{count ? ` (${count})` : ''}</NavLink>
}
