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

PLATFORM_GROUPS = {
    "PC": ["Steam", "EA App", "Ubisoft Connect", "Epic Games", "GOG.com", "Battle.net", "Microsoft Store"],
    "Consoles": ["Xbox Series X|S", "Xbox One", "PlayStation Store", "Switch"],
}

# id de catégorie Algolia (cat_ids) extraits des pages /discover/genres/ du site,
# aucune API publique ne les documente
GENRES = [
    {"slug": "action", "label": "Action", "cat_id": 1},
    {"slug": "adventure", "label": "Aventure", "cat_id": 4},
    {"slug": "rpg", "label": "RPG", "cat_id": 11},
    {"slug": "strategy", "label": "Stratégie", "cat_id": 17},
    {"slug": "simulation", "label": "Simulation", "cat_id": 15},
    {"slug": "sports", "label": "Sport", "cat_id": 16},
    {"slug": "racing", "label": "Course", "cat_id": 8},
    {"slug": "fighting", "label": "Combat", "cat_id": 7},
    {"slug": "fps", "label": "FPS", "cat_id": 9},
    {"slug": "platformer", "label": "Plateforme", "cat_id": 13},
    {"slug": "arcade", "label": "Arcade", "cat_id": 2},
    {"slug": "management", "label": "Gestion", "cat_id": 10},
    {"slug": "mmo", "label": "MMO", "cat_id": 12},
    {"slug": "multiplayer", "label": "Multijoueur", "cat_id": 23},
    {"slug": "online-co-op", "label": "Coop en ligne", "cat_id": 53},
    {"slug": "local-co-op", "label": "Coop en local", "cat_id": 54},
    {"slug": "online-pvp", "label": "PvP en ligne", "cat_id": 51},
    {"slug": "single-player", "label": "Solo", "cat_id": 47},
    {"slug": "indies", "label": "Indépendant", "cat_id": 32},
    {"slug": "free-to-play", "label": "Free-to-play", "cat_id": 35},
    {"slug": "early-access", "label": "Accès anticipé", "cat_id": 37},
    {"slug": "vr", "label": "Réalité virtuelle", "cat_id": 31},
    {"slug": "wargame", "label": "Wargame", "cat_id": 18},
]
GENRE_BY_SLUG = {g["slug"]: g["cat_id"] for g in GENRES}


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


# Algolia plafonne hitsPerPage à 1000 par requête ; au-delà, il faudrait paginer
# côté Algolia lui-même. Un seul appel à 1000 couvre la quasi-totalité des
# recherches/filtres réels ; le vrai total (nbHits) est toujours renvoyé pour
# rester honnête quand ce plafond est atteint.
ALGOLIA_MAX_HITS = 1000


async def search(query: str) -> tuple[list[Offer], int]:
    query = sanitize_title(query)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            ALGOLIA_URL,
            headers=HEADERS,
            json={"params": f"query={query}&hitsPerPage=100"},
        )
        resp.raise_for_status()
        data = resp.json()

    return [_hit_to_offer(h) for h in data.get("hits", [])], data.get("nbHits", 0)


async def discover(
    min_price: float | None = None,
    max_price: float | None = None,
    min_discount: int = 0,
    platform: str | None = None,
    genre: str | None = None,
    sort_by: str = "discount",
) -> tuple[list[Offer], int]:
    filters = ["is_dlc=0"]
    if min_price is not None:
        filters.append(f"price>={min_price}")
    if max_price is not None:
        filters.append(f"price<={max_price}")
    if min_discount:
        filters.append(f"discount>={min_discount}")
    if platform:
        if platform in PLATFORM_GROUPS:
            group_filter = " OR ".join(f'platform:"{p}"' for p in PLATFORM_GROUPS[platform])
            filters.append(f"({group_filter})")
        else:
            filters.append(f'platform:"{platform}"')
    if genre and genre in GENRE_BY_SLUG:
        filters.append(f"cat_ids:{GENRE_BY_SLUG[genre]}")

    params = f"query=&hitsPerPage={ALGOLIA_MAX_HITS}&filters={' AND '.join(filters)}"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(ALGOLIA_URL, headers=HEADERS, json={"params": params})
        resp.raise_for_status()
        data = resp.json()

    offers = [_hit_to_offer(h) for h in data.get("hits", [])]

    if sort_by == "price_asc":
        offers.sort(key=lambda o: (o.price is None, o.price))
    elif sort_by == "price_desc":
        offers.sort(key=lambda o: -(o.price or 0))
    else:
        offers.sort(key=lambda o: -(o.discount_percent or 0))

    return offers, data.get("nbHits", 0)
