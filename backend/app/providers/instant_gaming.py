import httpx

from ..schemas import Offer

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


async def search(query: str) -> list[Offer]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            ALGOLIA_URL,
            headers=HEADERS,
            json={"params": f"query={query}&hitsPerPage=5"},
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])

    offers: list[Offer] = []
    for hit in hits:
        offers.append(
            Offer(
                source="Instant Gaming",
                name=hit.get("fullname") or hit.get("name"),
                price=hit.get("price"),
                base_price=float(hit.get("retail", 0)) if hit.get("retail") else None,
                currency=hit.get("retail_currency", "EUR"),
                discount_percent=hit.get("discount"),
                url=f"https://www.instant-gaming.com/en/{hit['prod_id']}-{hit.get('seo_name', '')}/",
                platform=hit.get("platform"),
            )
        )
    return offers
