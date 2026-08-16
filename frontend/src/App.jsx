import { useEffect, useMemo, useRef, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const SOURCE_META = {
  'IsThereAnyDeal': { short: 'ITAD', color: '#6c5ce7' },
  'Instant Gaming': { short: 'IG', color: '#00d9a3' },
}

function sourceColor(source) {
  return SOURCE_META[source]?.color || '#4f8cff'
}

function OfferCard({ offer, index }) {
  const hasDiscount = !!offer.discount_percent
  return (
    <a
      className="card"
      href={offer.url}
      target="_blank"
      rel="noreferrer"
      style={{ '--accent': sourceColor(offer.source), animationDelay: `${index * 45}ms` }}
    >
      <div className="card-top">
        <span className="card-source">{offer.source}</span>
        <div className="card-top-right">
          {offer.platform && <span className="card-platform">{offer.platform}</span>}
          {hasDiscount && <span className="ribbon">-{offer.discount_percent}%</span>}
        </div>
      </div>
      <div className="card-name">{offer.name}</div>
      <div className="card-price-row">
        {offer.base_price && offer.base_price !== offer.price && (
          <span className="base-price">{offer.base_price} {offer.currency}</span>
        )}
        <span className="price">{offer.price != null ? `${offer.price} ${offer.currency}` : '—'}</span>
      </div>
      <div className="card-glow" />
    </a>
  )
}

function SkeletonCard({ index }) {
  return <div className="card skeleton" style={{ animationDelay: `${index * 60}ms` }} />
}

const SORT_OPTIONS = [
  { value: 'price-asc', label: 'Prix croissant' },
  { value: 'price-desc', label: 'Prix décroissant' },
  { value: 'discount-desc', label: 'Meilleure remise' },
  { value: 'name-asc', label: 'Nom (A-Z)' },
]

export default function App() {
  const [query, setQuery] = useState('')
  const [offers, setOffers] = useState([])
  const [errors, setErrors] = useState([])
  const [loading, setLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  const [activeSources, setActiveSources] = useState(new Set(Object.keys(SOURCE_META)))
  const [sortBy, setSortBy] = useState('price-asc')
  const [minDiscount, setMinDiscount] = useState(0)
  const [maxPrice, setMaxPrice] = useState('')

  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [activeSuggestion, setActiveSuggestion] = useState(-1)
  const debounceRef = useRef(null)
  const suggestAbortRef = useRef(null)
  const inputWrapRef = useRef(null)

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)

    const trimmed = query.trim()
    if (trimmed.length < 2) {
      setSuggestions([])
      setShowSuggestions(false)
      return
    }

    debounceRef.current = setTimeout(async () => {
      suggestAbortRef.current?.abort()
      const controller = new AbortController()
      suggestAbortRef.current = controller
      try {
        const res = await fetch(`${API_BASE}/api/suggest?q=${encodeURIComponent(trimmed)}`, {
          signal: controller.signal,
        })
        const data = await res.json()
        setSuggestions(Array.isArray(data) ? data : [])
        setShowSuggestions(true)
        setActiveSuggestion(-1)
      } catch {
        // requête annulée ou échouée silencieusement, pas critique pour l'UX
      }
    }, 250)

    return () => clearTimeout(debounceRef.current)
  }, [query])

  useEffect(() => {
    function handleClickOutside(e) {
      if (inputWrapRef.current && !inputWrapRef.current.contains(e.target)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  async function runSearch(term) {
    const value = term.trim()
    if (value.length < 2) return
    setShowSuggestions(false)
    setLoading(true)
    setErrors([])
    setHasSearched(true)
    try {
      const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(value)}`)
      const data = await res.json()
      setOffers(data.offers || [])
      setErrors(data.errors || [])
    } catch (err) {
      setErrors([String(err)])
    } finally {
      setLoading(false)
    }
  }

  function handleSearch(e) {
    e.preventDefault()
    runSearch(query)
  }

  function selectSuggestion(title) {
    setQuery(title)
    runSearch(title)
  }

  function handleKeyDown(e) {
    if (!showSuggestions || suggestions.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveSuggestion((i) => (i + 1) % suggestions.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveSuggestion((i) => (i - 1 + suggestions.length) % suggestions.length)
    } else if (e.key === 'Enter' && activeSuggestion >= 0) {
      e.preventDefault()
      selectSuggestion(suggestions[activeSuggestion])
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
    }
  }

  function toggleSource(source) {
    setActiveSources((prev) => {
      const next = new Set(prev)
      if (next.has(source)) next.delete(source)
      else next.add(source)
      return next
    })
  }

  const filteredOffers = useMemo(() => {
    let result = offers.filter((o) => activeSources.has(o.source))
    if (minDiscount > 0) {
      result = result.filter((o) => (o.discount_percent || 0) >= minDiscount)
    }
    if (maxPrice !== '' && !Number.isNaN(Number(maxPrice))) {
      result = result.filter((o) => o.price != null && o.price <= Number(maxPrice))
    }
    const sorted = [...result]
    switch (sortBy) {
      case 'price-desc':
        sorted.sort((a, b) => (b.price ?? -1) - (a.price ?? -1))
        break
      case 'discount-desc':
        sorted.sort((a, b) => (b.discount_percent || 0) - (a.discount_percent || 0))
        break
      case 'name-asc':
        sorted.sort((a, b) => a.name.localeCompare(b.name))
        break
      default:
        sorted.sort((a, b) => {
          if (a.price == null) return 1
          if (b.price == null) return -1
          return a.price - b.price
        })
    }
    return sorted
  }, [offers, activeSources, sortBy, minDiscount, maxPrice])

  const bestPrice = filteredOffers.reduce(
    (min, o) => (o.price != null && (min == null || o.price < min) ? o.price : min),
    null
  )

  return (
    <div className="app-bg">
      <div className="orb orb-1" />
      <div className="orb orb-2" />

      <div className="container">
        <header className="hero">
          <h1>
            <span className="brand-gradient">GameDeal</span> Aggregator
          </h1>
          <p className="subtitle">IsThereAnyDeal + Instant Gaming, comparés en un coup d'œil</p>
        </header>

        <form onSubmit={handleSearch} className="search-form">
          <div className="search-input-wrap" ref={inputWrapRef}>
            <svg className="search-icon" viewBox="0 0 24 24" width="18" height="18" fill="none">
              <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
              <path d="M20 20L16.65 16.65" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <input
              type="text"
              placeholder="Rechercher un jeu (ex: Sims, Elden Ring...)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
              onKeyDown={handleKeyDown}
              autoComplete="off"
            />
            {showSuggestions && suggestions.length > 0 && (
              <ul className="suggestions">
                {suggestions.map((title, i) => (
                  <li
                    key={title}
                    className={i === activeSuggestion ? 'active' : ''}
                    onMouseDown={() => selectSuggestion(title)}
                    onMouseEnter={() => setActiveSuggestion(i)}
                  >
                    {title}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button type="submit" disabled={loading} className="search-btn">
            {loading ? <span className="spinner" /> : 'Chercher'}
          </button>
        </form>

        {hasSearched && (
          <div className="filters">
            <div className="filter-group chips">
              {Object.keys(SOURCE_META).map((source) => (
                <button
                  key={source}
                  type="button"
                  className={`chip ${activeSources.has(source) ? 'active' : ''}`}
                  style={{ '--chip-color': sourceColor(source) }}
                  onClick={() => toggleSource(source)}
                >
                  {SOURCE_META[source].short}
                </button>
              ))}
            </div>

            <div className="filter-group">
              <label htmlFor="sort">Trier par</label>
              <select id="sort" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            <div className="filter-group">
              <label htmlFor="discount">Remise min. {minDiscount > 0 ? `${minDiscount}%` : ''}</label>
              <input
                id="discount"
                type="range"
                min="0"
                max="90"
                step="5"
                value={minDiscount}
                onChange={(e) => setMinDiscount(Number(e.target.value))}
              />
            </div>

            <div className="filter-group">
              <label htmlFor="maxprice">Prix max (€)</label>
              <input
                id="maxprice"
                type="number"
                min="0"
                placeholder="illimité"
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
                className="price-input"
              />
            </div>
          </div>
        )}

        {errors.length > 0 && (
          <div className="errors">
            {errors.map((err, i) => <div key={i}>⚠ {err}</div>)}
          </div>
        )}

        {hasSearched && !loading && (
          <div className="result-meta">
            {filteredOffers.length} résultat{filteredOffers.length !== 1 ? 's' : ''}
            {bestPrice != null && (
              <span className="best-price-badge">meilleur prix : {bestPrice.toFixed(2)} €</span>
            )}
          </div>
        )}

        <div className="grid">
          {loading && Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} index={i} />)}
          {!loading && filteredOffers.map((offer, i) => (
            <OfferCard key={`${offer.source}-${offer.name}-${i}`} offer={offer} index={i} />
          ))}
        </div>

        {!loading && hasSearched && filteredOffers.length === 0 && (
          <div className="empty-state">
            <p>Aucune offre ne correspond à ces filtres.</p>
          </div>
        )}

        {!hasSearched && (
          <div className="empty-state">
            <p>Lance une recherche pour comparer les prix.</p>
          </div>
        )}
      </div>
    </div>
  )
}
