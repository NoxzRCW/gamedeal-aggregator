import httpx

from ..schemas import Offer
from ..text_utils import sanitize_title

ALGOLIA_APP_ID = "QKNHP8TC3Y"
ALGOLIA_API_KEY = "93946b91c013211f842ddf1819ea880b"
ALGOLIA_URL = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/produits_en/query"

HEADERS = {
    "X-Algolia-API-Key": ALGOLIA_API_KEY,
    "X-Algolia-Application-Id": ALGOLIA_APP_ID,
    "Content-Type": "application/json",
    "Referer": "https://www.instant-gaming.com/",
    "Origin": "https://www.instant-gaming.com",
}

PLATFORMS = [
    "Steam",
    "Xbox Series X|S",
    "Xbox One",
    "Switch",
    "PlayStation Store",
    "EA App",
    "Ubisoft Connect",
    "Epic Games",
    "GOG.com",
    "Battle.net",
]


def _cover_url(hit: dict) -> str | None:
    seo_name = hit.get("seo_name")
    updated_at = hit.get("updated_at")
    if not seo_name:
        return None
    url = f"https://gaming-cdn.com/images/products/{hit['prod_id']}/380x218/{seo_name}-cover.jpg"
    if updated_at:
        url += f"?v={updated_at}"
    return url


def _hit_to_offer(hit: dict) -> Offer:
    return Offer(
        source="Instant Gaming",
        name=hit.get("fullname") or hit.get("name"),
        price=hit.get("price"),
        base_price=float(hit.get("retail", 0)) if hit.get("retail") else None,
        currency=hit.get("retail_currency", "EUR"),
        discount_percent=hit.get("discount"),
        url=f"https://www.instant-gaming.com/en/{hit['prod_id']}-{hit.get('seo_name', '')}/",
        platform=hit.get("platform"),
        image=_cover_url(hit),
    )


async def search(query: str) -> list[Offer]:
    query = sanitize_title(query)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            ALGOLIA_URL,
            headers=HEADERS,
            json={"params": f"query={query}&hitsPerPage=5"},
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])

    return [_hit_to_offer(h) for h in hits]


async def discover(
    min_price: float | None = None,
    max_price: float | None = None,
    min_discount: int = 0,
    platform: str | None = None,
    sort_by: str = "discount",
    limit: int = 24,
) -> list[Offer]:
    filters = ["is_dlc=0"]
    if min_price is not None:
        filters.append(f"price>={min_price}")
    if max_price is not None:
        filters.append(f"price<={max_price}")
    if min_discount:
        filters.append(f"discount>={min_discount}")
    if platform:
        filters.append(f'platform:"{platform}"')

    params = f"query=&hitsPerPage=60&filters={' AND '.join(filters)}"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(ALGOLIA_URL, headers=HEADERS, json={"params": params})
        resp.raise_for_status()
        hits = resp.json().get("hits", [])

    offers = [_hit_to_offer(h) for h in hits]

    if sort_by == "price_asc":
        offers.sort(key=lambda o: (o.price is None, o.price))
    elif sort_by == "price_desc":
        offers.sort(key=lambda o: -(o.price or 0))
    else:
        offers.sort(key=lambda o: -(o.discount_percent or 0))

    return offers[:limit]
