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
    return instant_gaming.PLATFORM_GROUPS


@app.get("/api/genres")
async def genres():
    return instant_gaming.GENRES


@app.get("/api/discover", response_model=SearchResponse)
async def discover(
    min_price: float | None = None,
    max_price: float | None = None,
    min_discount: int = 0,
    platform: str | None = None,
    genre: str | None = None,
    sort_by: str = "discount",
    include_dlc: bool = False,
    offset: int = 0,
    page_size: int = 24,
):
    # le résultat complet (jusqu'à 1000, trié) est mis en cache une fois pour tous
    # les offsets d'une même combinaison de filtres, évitant de refaire l'appel
    # Algolia à chaque clic sur "Charger plus"
    cache_key = f"discover:{min_price}:{max_price}:{min_discount}:{platform}:{genre}:{sort_by}:{include_dlc}"
    cached = await cache_get(cache_key)
    if cached is not None:
        all_offers, total, errors = cached["offers"], cached["total"], cached["errors"]
    else:
        try:
            offers, total = await instant_gaming.discover(
                min_price=min_price,
                max_price=max_price,
                min_discount=min_discount,
                platform=platform,
                genre=genre,
                sort_by=sort_by,
                include_dlc=include_dlc,
            )
            errors = []
        except Exception as exc:
            offers, total = [], 0
            errors = [f"instant_gaming: {exc}"]

        all_offers = [o.model_dump() for o in offers]
        await cache_set(cache_key, {"offers": all_offers, "total": total, "errors": errors}, ttl=600)

    page = all_offers[offset : offset + page_size]
    return SearchResponse(
        query="",
        offers=page,
        errors=errors,
        total=total,
        loaded_total=len(all_offers),
        has_more=offset + page_size < len(all_offers),
    )


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
async def search(
    q: str = Query(min_length=2),
    include_dlc: bool = False,
    offset: int = 0,
    page_size: int = 24,
):
    cache_key = f"search:{q.lower()}:{include_dlc}"
    cached = await cache_get(cache_key)
    if cached is not None:
        all_offers = cached["offers"]
        bundle_deals_cached = cached["bundle_deals"]
        errors = cached["errors"]
        total = cached["total"]
        page = all_offers[offset : offset + page_size]
        return SearchResponse(
            query=q,
            offers=page,
            bundle_deals=bundle_deals_cached,
            errors=errors,
            total=total,
            loaded_total=len(all_offers),
            has_more=offset + page_size < len(all_offers),
        )

    results = await asyncio.gather(
        itad.search(q, include_dlc=include_dlc),
        instant_gaming.search(q, include_dlc=include_dlc),
        get_humble_index(),
        return_exceptions=True,
    )
    itad_result, ig_result, humble_index = results

    offers = []
    errors = []
    ig_total = 0
    for source_name, result in [("itad", itad_result), ("instant_gaming", ig_result)]:
        if isinstance(result, Exception):
            errors.append(f"{source_name}: {result}")
        elif source_name == "instant_gaming":
            ig_offers, ig_total = result
            offers.extend(ig_offers)
        else:
            offers.extend(result)

    offers.sort(key=lambda o: (o.price is None, o.price))
    total = len(offers) + max(ig_total - sum(1 for o in offers if o.source == "Instant Gaming"), 0)

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
            relevant_best = min((o.price for o in relevant_offers), default=None)

            entry_price = match["entry_price"]
            item_msrp = match.get("matched_item_msrp") or 0
            total_value = match.get("total_value") or 0
            other_items_value = round(max(total_value - item_msrp, 0), 2)

            deal_type = None
            savings = None
            extra_cost = None

            if relevant_best is not None and entry_price < relevant_best:
                # cas simple : le bundle est directement moins cher que le jeu ciblé seul
                deal_type = "cheaper"
                savings = round(relevant_best - entry_price, 2)
            elif relevant_best is not None and entry_price >= relevant_best and other_items_value > 0:
                # le jeu seul est moins cher, mais les AUTRES jeux du bundle peuvent
                # rendre l'ensemble plus rentable si leur valeur dépasse largement le surcoût
                extra_cost = round(entry_price - relevant_best, 2)
                if other_items_value >= extra_cost * 3:
                    deal_type = "value"
            elif relevant_best is None and item_msrp:
                # pas d'offre solo trouvée pour ce jeu précis : on compare au prix officiel
                if entry_price < item_msrp * 0.6:
                    deal_type = "cheaper"
                    savings = round(item_msrp - entry_price, 2)

            if deal_type:
                bundle_deals.append(
                    BundleDeal(
                        **match,
                        savings=savings,
                        deal_type=deal_type,
                        extra_cost=extra_cost,
                        other_items_value=other_items_value or None,
                    )
                )
        bundle_deals.sort(key=lambda d: (d.deal_type != "cheaper", d.entry_price))

    all_offers = [o.model_dump() for o in offers]
    bundle_deals_dump = [b.model_dump() for b in bundle_deals]
    await cache_set(
        cache_key,
        {"offers": all_offers, "bundle_deals": bundle_deals_dump, "errors": errors, "total": total},
    )

    page = all_offers[offset : offset + page_size]
    return SearchResponse(
        query=q,
        offers=page,
        bundle_deals=bundle_deals_dump,
        errors=errors,
        total=total,
        loaded_total=len(all_offers),
        has_more=offset + page_size < len(all_offers),
    )
