import { useState } from 'react'
import { useNavigate } from 'react-router'
import { paramsFromQuery } from '../lib/query'

export function Search() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const [isbn, setIsbn] = useState('')
  const ready = Boolean(title.trim() || isbn.trim())

  return (
    <section>
      <h1>Find a book</h1>
      <p className="muted">Search by title (and author), or by ISBN.</p>
      <form
        className="search"
        onSubmit={(e) => {
          e.preventDefault()
          if (ready) navigate(`/book?${paramsFromQuery({ title, author, isbn })}`)
        }}
      >
        <label>Title <input value={title} onChange={(e) => setTitle(e.target.value)} /></label>
        <label>Author <input value={author} onChange={(e) => setAuthor(e.target.value)} /></label>
        <label>ISBN <input value={isbn} onChange={(e) => setIsbn(e.target.value)} inputMode="numeric" /></label>
        <button type="submit" disabled={!ready}>Search</button>
      </form>
    </section>
  )
}
