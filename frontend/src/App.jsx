import { useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

function OfferCard({ offer }) {
  return (
    <a className="card" href={offer.url} target="_blank" rel="noreferrer">
      <div className="card-source">{offer.source}</div>
      <div className="card-name">{offer.name}</div>
      <div className="card-platform">{offer.platform}</div>
      <div className="card-price-row">
        {offer.base_price && offer.base_price !== offer.price && (
          <span className="base-price">{offer.base_price} {offer.currency}</span>
        )}
        <span className="price">{offer.price != null ? `${offer.price} ${offer.currency}` : '—'}</span>
        {offer.discount_percent ? <span className="discount">-{offer.discount_percent}%</span> : null}
      </div>
    </a>
  )
}

export default function App() {
  const [query, setQuery] = useState('')
  const [offers, setOffers] = useState([])
  const [errors, setErrors] = useState([])
  const [loading, setLoading] = useState(false)

  async function handleSearch(e) {
    e.preventDefault()
    if (query.trim().length < 2) return
    setLoading(true)
    setErrors([])
    try {
      const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}`)
      const data = await res.json()
      setOffers(data.offers || [])
      setErrors(data.errors || [])
    } catch (err) {
      setErrors([String(err)])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <h1>GameDeal Aggregator</h1>
      <p className="subtitle">IsThereAnyDeal + Instant Gaming, prix comparés en un coup d'œil</p>

      <form onSubmit={handleSearch} className="search-form">
        <input
          type="text"
          placeholder="Rechercher un jeu (ex: Elden Ring)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Recherche...' : 'Chercher'}
        </button>
      </form>

      {errors.length > 0 && (
        <div className="errors">
          {errors.map((err, i) => <div key={i}>{err}</div>)}
        </div>
      )}

      <div className="grid">
        {offers.map((offer, i) => (
          <OfferCard key={i} offer={offer} />
        ))}
      </div>

      {!loading && offers.length === 0 && (
        <p className="empty">Aucun résultat pour l'instant. Lance une recherche.</p>
      )}
    </div>
  )
}
