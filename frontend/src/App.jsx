import { useEffect, useMemo, useRef, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const SOURCE_META = {
  'IsThereAnyDeal': { short: 'ITAD', color: '#6c5ce7' },
  'Instant Gaming': { short: 'IG', color: '#00d9a3' },
}

function sourceColor(source) {
  return SOURCE_META[source]?.color || '#4f8cff'
}

function OfferCard({ offer, index, onOpenDetails }) {
  const hasDiscount = !!offer.discount_percent
  return (
    <div
      className="card"
      style={{ '--accent': sourceColor(offer.source), animationDelay: `${index * 45}ms` }}
      onClick={() => onOpenDetails(offer)}
      role="button"
      tabIndex={0}
    >
      {offer.image && (
        <div className="card-cover">
          <img src={offer.image} alt="" loading="lazy" />
          <span className="card-cover-hint">Voir les infos</span>
        </div>
      )}
      <div className="card-body">
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
        <a
          className="buy-link"
          href={offer.url}
          target="_blank"
          rel="noreferrer"
          onClick={(e) => e.stopPropagation()}
        >
          Acheter sur {offer.source} ↗
        </a>
      </div>
      <div className="card-glow" />
    </div>
  )
}

function ScoreBadge({ source, score }) {
  const good = score >= 75
  const mid = score >= 50
  return (
    <div className={`score-badge ${good ? 'good' : mid ? 'mid' : 'low'}`}>
      <span className="score-value">{score}</span>
      <span className="score-source">{source}</span>
    </div>
  )
}

function GameDetailsModal({ offer, onClose }) {
  const [details, setDetails] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (!offer) return
    setDetails(null)
    setNotFound(false)
    setLoading(true)
    fetch(`${API_BASE}/api/details?title=${encodeURIComponent(offer.name)}`)
      .then((res) => res.json())
      .then((data) => {
        if (!data) setNotFound(true)
        else setDetails(data)
      })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false))
  }, [offer])

  useEffect(() => {
    function handleKey(e) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  if (!offer) return null

  const hero = details?.header_image || details?.banner || offer.image

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Fermer">✕</button>

        {hero && (
          <div className="modal-hero">
            <img src={hero} alt="" />
            <div className="modal-hero-fade" />
          </div>
        )}

        <div className="modal-content">
          <h2>{offer.name}</h2>

          {loading && <div className="modal-loading"><span className="spinner" /> Chargement des infos...</div>}

          {!loading && notFound && (
            <p className="modal-empty">Pas de détails disponibles pour ce jeu, mais tu peux toujours consulter l'offre.</p>
          )}

          {!loading && details && (
            <>
              {details.description && <p className="modal-description">{details.description}</p>}

              {details.reviews?.length > 0 && (
                <div className="score-row">
                  {details.reviews.map((r) => (
                    <ScoreBadge key={r.source} source={r.source} score={r.score} />
                  ))}
                </div>
              )}

              {details.genres?.length > 0 && (
                <div className="tag-row">
                  {details.genres.map((g) => <span key={g} className="tag genre">{g}</span>)}
                </div>
              )}

              {details.tags?.length > 0 && (
                <div className="tag-row">
                  {details.tags.map((t) => <span key={t} className="tag">{t}</span>)}
                </div>
              )}

              <div className="modal-meta">
                {details.release_date && <span>📅 {details.release_date}</span>}
                {details.developers?.length > 0 && <span>🛠 {details.developers.join(', ')}</span>}
              </div>

              {details.categories?.length > 0 && (
                <div className="tag-row muted-tags">
                  {details.categories.map((c) => <span key={c} className="tag outline">{c}</span>)}
                </div>
              )}

              {details.screenshots?.length > 0 && (
                <div className="screenshot-row">
                  {details.screenshots.map((s) => (
                    <img key={s} src={s} alt="" loading="lazy" />
                  ))}
                </div>
              )}
            </>
          )}

          <div className="modal-offer">
            <div>
              {offer.base_price && offer.base_price !== offer.price && (
                <span className="base-price">{offer.base_price} {offer.currency}</span>
              )}
              <span className="price big">{offer.price != null ? `${offer.price} ${offer.currency}` : '—'}</span>
            </div>
            <a className="search-btn" href={offer.url} target="_blank" rel="noreferrer">
              Acheter sur {offer.source} ↗
            </a>
          </div>
        </div>
      </div>
    </div>
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

function SearchTab({ onOpenDetails }) {
  const [query, setQuery] = useState('')
  const [offers, setOffers] = useState([])
  const [bundleDeals, setBundleDeals] = useState([])
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
      setBundleDeals(data.bundle_deals || [])
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

  function selectSuggestion(entry) {
    setQuery(entry.title)
    runSearch(entry.title)
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
    <>
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
              {suggestions.map((entry, i) => (
                <li
                  key={entry.title}
                  className={i === activeSuggestion ? 'active' : ''}
                  onMouseDown={() => selectSuggestion(entry)}
                  onMouseEnter={() => setActiveSuggestion(i)}
                >
                  <span className="suggestion-thumb">
                    {entry.image ? (
                      <img src={entry.image} alt="" loading="lazy" />
                    ) : (
                      <span className="suggestion-thumb-fallback">🎮</span>
                    )}
                  </span>
                  <span className="suggestion-text">
                    <span className="suggestion-title">{entry.title}</span>
                    {entry.type && entry.type !== 'game' && (
                      <span className="suggestion-type">{entry.type}</span>
                    )}
                  </span>
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

      {!loading && bundleDeals.length > 0 && (
        <div className="bundle-callouts">
          {bundleDeals.map((b) => (
            <a key={b.bundle_url} href={b.bundle_url} target="_blank" rel="noreferrer" className="bundle-callout">
              {b.bundle_image && <img src={b.bundle_image} alt="" className="bundle-callout-img" />}
              <div className="bundle-callout-body">
                <div className="bundle-callout-tag">💡 Meilleur plan : bundle</div>
                <div className="bundle-callout-title">{b.bundle_title}</div>
                <div className="bundle-callout-text">
                  "{b.matched_item}" + {b.items_count - 1} autre{b.items_count - 1 !== 1 ? 's' : ''} jeu{b.items_count - 1 !== 1 ? 'x' : ''} pour <strong>{b.entry_price.toFixed(2)} {b.currency}</strong>
                  {b.savings != null && b.savings > 0 && (
                    <span className="bundle-savings"> · économise {b.savings.toFixed(2)} €</span>
                  )}
                </div>
              </div>
            </a>
          ))}
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
          <OfferCard key={`${offer.source}-${offer.name}-${i}`} offer={offer} index={i} onOpenDetails={onOpenDetails} />
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
    </>
  )
}

const DISCOVER_SORT_OPTIONS = [
  { value: 'discount', label: 'Meilleure remise' },
  { value: 'price_asc', label: 'Prix croissant' },
  { value: 'price_desc', label: 'Prix décroissant' },
]

function DiscoverTab({ onOpenDetails }) {
  const [platforms, setPlatforms] = useState([])
  const [platform, setPlatform] = useState('')
  const [maxPrice, setMaxPrice] = useState(20)
  const [minDiscount, setMinDiscount] = useState(50)
  const [sortBy, setSortBy] = useState('discount')

  const [offers, setOffers] = useState([])
  const [errors, setErrors] = useState([])
  const [loading, setLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  useEffect(() => {
    fetch(`${API_BASE}/api/platforms`)
      .then((res) => res.json())
      .then((data) => setPlatforms(Array.isArray(data) ? data : []))
      .catch(() => {})
  }, [])

  async function runDiscover() {
    setLoading(true)
    setErrors([])
    setHasSearched(true)
    try {
      const params = new URLSearchParams()
      if (maxPrice !== '') params.set('max_price', maxPrice)
      if (minDiscount > 0) params.set('min_discount', minDiscount)
      if (platform) params.set('platform', platform)
      params.set('sort_by', sortBy)

      const res = await fetch(`${API_BASE}/api/discover?${params.toString()}`)
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
    <>
      <div className="discover-intro">
        <p>Pas d'idée précise ? Fixe tes critères et découvre des jeux en promo.</p>
      </div>

      <div className="filters discover-filters">
        <div className="filter-group">
          <label htmlFor="d-platform">Plateforme</label>
          <select id="d-platform" value={platform} onChange={(e) => setPlatform(e.target.value)}>
            <option value="">Toutes</option>
            {platforms.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="d-price">Prix max : {maxPrice === '' ? 'illimité' : `${maxPrice} €`}</label>
          <input
            id="d-price"
            type="range"
            min="0"
            max="80"
            step="5"
            value={maxPrice === '' ? 80 : maxPrice}
            onChange={(e) => setMaxPrice(Number(e.target.value))}
          />
        </div>

        <div className="filter-group">
          <label htmlFor="d-discount">Remise min. {minDiscount}%</label>
          <input
            id="d-discount"
            type="range"
            min="0"
            max="90"
            step="5"
            value={minDiscount}
            onChange={(e) => setMinDiscount(Number(e.target.value))}
          />
        </div>

        <div className="filter-group">
          <label htmlFor="d-sort">Trier par</label>
          <select id="d-sort" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            {DISCOVER_SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <button type="button" className="search-btn discover-btn" onClick={runDiscover} disabled={loading}>
          {loading ? <span className="spinner" /> : "Trouver des idées"}
        </button>
      </div>

      {errors.length > 0 && (
        <div className="errors">
          {errors.map((err, i) => <div key={i}>⚠ {err}</div>)}
        </div>
      )}

      {hasSearched && !loading && (
        <div className="result-meta">{offers.length} suggestion{offers.length !== 1 ? 's' : ''}</div>
      )}

      <div className="grid">
        {loading && Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} index={i} />)}
        {!loading && offers.map((offer, i) => (
          <OfferCard key={`${offer.source}-${offer.name}-${i}`} offer={offer} index={i} onOpenDetails={onOpenDetails} />
        ))}
      </div>

      {!loading && hasSearched && offers.length === 0 && (
        <div className="empty-state">
          <p>Aucune offre ne correspond à ces critères, élargis un peu.</p>
        </div>
      )}

      {!hasSearched && (
        <div className="empty-state">
          <p>Règle tes critères puis lance "Trouver des idées".</p>
        </div>
      )}
    </>
  )
}

function BundleCard({ bundle, index }) {
  return (
    <a
      className="card bundle-card"
      href={bundle.url}
      target="_blank"
      rel="noreferrer"
      style={{ animationDelay: `${index * 45}ms` }}
    >
      {bundle.image && (
        <div className="card-cover">
          <img src={bundle.image} alt="" loading="lazy" />
        </div>
      )}
      <div className="card-body">
        <div className="card-name">{bundle.title}</div>
        {bundle.blurb && <p className="bundle-blurb">{bundle.blurb}</p>}
        <div className="tag-row">
          {bundle.highlights?.map((h) => <span key={h} className="tag outline">{h}</span>)}
        </div>
        <div className="card-price-row">
          <span className="price">
            {bundle.entry_price != null ? `dès ${bundle.entry_price.toFixed(2)} ${bundle.currency}` : 'Pay What You Want'}
          </span>
        </div>
        {bundle.end_date && (
          <div className="bundle-end-date">⏳ jusqu'au {new Date(bundle.end_date).toLocaleDateString('fr-FR')}</div>
        )}
      </div>
    </a>
  )
}

function BundlesTab() {
  const [bundles, setBundles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    fetch(`${API_BASE}/api/bundles`)
      .then((res) => res.json())
      .then((data) => setBundles(Array.isArray(data) ? data : []))
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false))
  }, [])

  return (
    <>
      <div className="discover-intro">
        <p>Bundles Humble Bundle actifs : plusieurs jeux pour un seul prix, souvent bien plus rentable qu'à l'unité.</p>
      </div>

      {error && <div className="errors">⚠ {error}</div>}

      <div className="grid">
        {loading && Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} index={i} />)}
        {!loading && bundles.map((b, i) => (
          <BundleCard key={b.machine_name} bundle={b} index={i} />
        ))}
      </div>

      {!loading && bundles.length === 0 && !error && (
        <div className="empty-state">
          <p>Aucun bundle actif pour le moment.</p>
        </div>
      )}
    </>
  )
}

export default function App() {
  const [tab, setTab] = useState('search')
  const [detailsOffer, setDetailsOffer] = useState(null)

  return (
    <div className="app-bg">
      <div className="orb orb-1" />
      <div className="orb orb-2" />

      <div className="container">
        <header className="hero">
          <h1>
            <span className="brand-gradient">GameDeal</span> Aggregator
          </h1>
          <p className="subtitle">ITAD + Instant Gaming + Humble Bundle, comparés en un coup d'œil</p>
        </header>

        <nav className="tabs">
          <button
            type="button"
            className={`tab ${tab === 'search' ? 'active' : ''}`}
            onClick={() => setTab('search')}
          >
            🔍 Rechercher
          </button>
          <button
            type="button"
            className={`tab ${tab === 'discover' ? 'active' : ''}`}
            onClick={() => setTab('discover')}
          >
            ✨ Idées
          </button>
          <button
            type="button"
            className={`tab ${tab === 'bundles' ? 'active' : ''}`}
            onClick={() => setTab('bundles')}
          >
            📦 Bundles
          </button>
        </nav>

        {tab === 'search' && <SearchTab onOpenDetails={setDetailsOffer} />}
        {tab === 'discover' && <DiscoverTab onOpenDetails={setDetailsOffer} />}
        {tab === 'bundles' && <BundlesTab />}
      </div>

      {detailsOffer && <GameDetailsModal offer={detailsOffer} onClose={() => setDetailsOffer(null)} />}
    </div>
  )
}
