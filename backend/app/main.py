import asyncio

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .cache import cache_get, cache_set
from .config import settings
from .providers import details as details_provider
from .providers import instant_gaming, itad
from .schemas import SearchResponse

app = FastAPI(title="GameDeal Aggregator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origins] if settings.cors_origins != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        itad.search(q), instant_gaming.search(q), return_exceptions=True
    )

    offers = []
    errors = []
    for source_name, result in zip(["itad", "instant_gaming"], results):
        if isinstance(result, Exception):
            errors.append(f"{source_name}: {result}")
        else:
            offers.extend(result)

    offers.sort(key=lambda o: (o.price is None, o.price))

    response = SearchResponse(query=q, offers=offers, errors=errors)
    await cache_set(cache_key, response.model_dump())
    return response
