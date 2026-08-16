import asyncio

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .cache import cache_get, cache_set
from .config import settings
from .providers import details as details_provider
from .providers import humble, instant_gaming, itad
from .schemas import Bundle, BundleDeal, SearchResponse

app = FastAPI(title="GameDeal Aggregator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origins] if settings.cors_origins != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HUMBLE_INDEX_CACHE_KEY = "humble:index"
HUMBLE_INDEX_TTL = 1800


async def get_humble_index() -> dict:
    cached = await cache_get(HUMBLE_INDEX_CACHE_KEY)
    if cached is not None:
        return cached
    try:
        index = await humble.build_deal_index()
    except Exception:
        index = {}
    await cache_set(HUMBLE_INDEX_CACHE_KEY, index, ttl=HUMBLE_INDEX_TTL)
    return index


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/suggest")
async def suggest(q: str = Query(min_length=1)):
    cache_key = f"suggest:{q.lower()}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    titles = await itad.suggest(q)
    await cache_set(cache_key, titles, ttl=3600)
    return titles


@app.get("/api/platforms")
async def platforms():
    return instant_gaming.PLATFORMS


@app.get("/api/discover", response_model=SearchResponse)
async def discover(
    min_price: float | None = None,
    max_price: float | None = None,
    min_discount: int = 0,
    platform: str | None = None,
    sort_by: str = "discount",
):
    cache_key = f"discover:{min_price}:{max_price}:{min_discount}:{platform}:{sort_by}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    try:
        offers = await instant_gaming.discover(
            min_price=min_price,
            max_price=max_price,
            min_discount=min_discount,
            platform=platform,
            sort_by=sort_by,
        )
        errors = []
    except Exception as exc:
        offers = []
        errors = [f"instant_gaming: {exc}"]

    response = SearchResponse(query="", offers=offers, errors=errors)
    await cache_set(cache_key, response.model_dump(), ttl=600)
    return response


@app.get("/api/bundles", response_model=list[Bundle])
async def bundles(category: str = "games"):
    cache_key = f"bundles:{category}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        data = await humble.list_bundles(category)
    except Exception:
        data = []
    await cache_set(cache_key, data, ttl=1800)
    return data


@app.get("/api/details")
async def details(title: str = Query(min_length=2)):
    cache_key = f"details:{title.lower()}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    data = await details_provider.get_details(title)
    await cache_set(cache_key, data, ttl=86400)
    return data


@app.get("/api/search", response_model=SearchResponse)
async def search(q: str = Query(min_length=2)):
    cache_key = f"search:{q.lower()}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    results = await asyncio.gather(
        itad.search(q), instant_gaming.search(q), get_humble_index(), return_exceptions=True
    )
    itad_result, ig_result, humble_index = results

    offers = []
    errors = []
    for source_name, result in [("itad", itad_result), ("instant_gaming", ig_result)]:
        if isinstance(result, Exception):
            errors.append(f"{source_name}: {result}")
        else:
            offers.extend(result)

    offers.sort(key=lambda o: (o.price is None, o.price))

    bundle_deals: list[BundleDeal] = []
    if isinstance(humble_index, dict) and humble_index:
        raw_matches = humble.find_in_index(humble_index, q)
        seen_bundles = set()
        for match in raw_matches:
            if match["bundle_url"] in seen_bundles:
                continue
            seen_bundles.add(match["bundle_url"])

            item_key = match["matched_item"].lower()
            # ne compare qu'aux offres qui correspondent vraiment au jeu du bundle,
            # pas au premier résultat de recherche fuzzy sans rapport
            relevant_offers = [
                o
                for o in offers
                if o.price is not None and (item_key in o.name.lower() or o.name.lower() in item_key)
            ]

            if relevant_offers:
                relevant_best = min(o.price for o in relevant_offers)
                is_better = match["entry_price"] < relevant_best
                savings = round(relevant_best - match["entry_price"], 2)
            elif match.get("matched_item_msrp"):
                # pas d'offre individuelle trouvée : on compare au prix officiel (MSRP)
                # et on n'affiche que si le gain est net, pour éviter le bruit
                is_better = match["entry_price"] < match["matched_item_msrp"] * 0.6
                savings = round(match["matched_item_msrp"] - match["entry_price"], 2)
            else:
                is_better = False
                savings = None

            if is_better:
                bundle_deals.append(BundleDeal(**match, savings=savings))
        bundle_deals.sort(key=lambda d: d.entry_price)

    response = SearchResponse(query=q, offers=offers, bundle_deals=bundle_deals, errors=errors)
    await cache_set(cache_key, response.model_dump())
    return response
