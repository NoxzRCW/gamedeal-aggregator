import httpx

from ..config import settings
from ..schemas import Offer
from ..text_utils import sanitize_title as _sanitize_title

BASE_URL = "https://api.isthereanydeal.com"

# ITAD ne couvre que les boutiques PC dématérialisées (pas de PlayStation/Xbox/Switch) ;
# ids récupérés via GET /service/shops/v1
SHOP_IDS = {
    "Steam": 61,
    "EA App": 52,
    "Ubisoft Connect": 62,
    "Epic Games": 16,
    "GOG.com": 35,
    "Microsoft Store": 48,
}
PC_SHOP_IDS = list(SHOP_IDS.values())


async def suggest(query: str, limit: int = 8) -> list[dict]:
    if not settings.itad_api_key:
        return []

    query = _sanitize_title(query)

    async with httpx.AsyncClient(timeout=6) as client:
        resp = await client.get(
            f"{BASE_URL}/games/search/v1",
            params={"key": settings.itad_api_key, "title": query, "results": max(limit * 4, 30)},
        )
        resp.raise_for_status()
        games = resp.json()

    seen = set()
    entries = []
    for g in games:
        title = g["title"]
        if title.lower() not in seen:
            seen.add(title.lower())
            assets = g.get("assets") or {}
            entries.append(
                {
                    "title": title,
                    "type": g.get("type", "game"),
                    "image": assets.get("boxart") or assets.get("banner145"),
                }
            )

    q = query.strip().lower()

    def rank(entry: dict) -> tuple[int, int]:
        low = entry["title"].lower()
        if low.startswith(q):
            return (0, len(low))
        # match au début d'un mot ("the sims" pour "sims")
        if any(word.startswith(q) for word in low.split()):
            return (1, len(low))
        return (2, len(low))

    entries.sort(key=rank)
    return entries[:limit]


async def search(query: str, include_dlc: bool = False) -> list[Offer]:
    if not settings.itad_api_key:
        raise RuntimeError("ITAD_API_KEY manquant")

    query = _sanitize_title(query)

    async with httpx.AsyncClient(timeout=10) as client:
        lookup = await client.get(
            f"{BASE_URL}/games/search/v1",
            params={"key": settings.itad_api_key, "title": query, "results": 100},
        )
        lookup.raise_for_status()
        games = lookup.json()
        if not games:
            return []

        game_ids = [g["id"] for g in games]
        prices_resp = await client.post(
            f"{BASE_URL}/games/prices/v3",
            params={"key": settings.itad_api_key, "country": "FR"},
            json=game_ids,
        )
        prices_resp.raise_for_status()
        price_data = {p["id"]: p for p in prices_resp.json()}

    offers: list[Offer] = []
    for game in games:
        is_dlc = game.get("type") == "dlc"
        if is_dlc and not include_dlc:
            continue
        entry = price_data.get(game["id"])
        if not entry or not entry.get("deals"):
            continue
        best = entry["deals"][0]
        assets = game.get("assets") or {}
        offers.append(
            Offer(
                source="IsThereAnyDeal",
                name=game["title"],
                price=best["price"]["amount"],
                base_price=best["regular"]["amount"],
                currency=best["price"]["currency"],
                discount_percent=best["cut"],
                url=best["url"],
                platform=best["shop"]["name"],
                image=assets.get("boxart") or assets.get("banner145"),
                is_dlc=is_dlc,
            )
        )
    return offers


async def discover(
    min_price: float | None = None,
    max_price: float | None = None,
    min_discount: int = 0,
    platform: str | None = None,
    include_dlc: bool = False,
    sort_by: str = "discount",
) -> tuple[list[Offer], int]:
    """Parcourt les deals ITAD actuels (PC uniquement) selon des critères prix/remise/boutique.

    Retourne une liste vide sans erreur quand le filtre plateforme cible une
    console (Xbox/PlayStation/Switch) : ITAD ne couvre pas ces boutiques.
    """
    if not settings.itad_api_key:
        raise RuntimeError("ITAD_API_KEY manquant")

    shops: list[int] | None = None
    if platform:
        if platform == "PC":
            shops = PC_SHOP_IDS
        elif platform == "Consoles":
            return [], 0
        elif platform in SHOP_IDS:
            shops = [SHOP_IDS[platform]]
        else:
            # plateforme console spécifique non couverte par ITAD
            return [], 0

    sort_map = {"discount": "-cut", "price_asc": "price", "price_desc": "-price"}
    body = {
        "country": "FR",
        "offset": 0,
        "limit": 200,
        "sort": sort_map.get(sort_by, "-cut"),
        "filter": {
            "cut": {"min": min_discount or 0, "max": None},
            "price": {"min": None, "max": max_price},
            "type": [1] if not include_dlc else [1, 2],
        },
    }
    if min_price is not None:
        body["filter"]["price"]["min"] = min_price
    if shops is not None:
        body["shops"] = shops

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{BASE_URL}/deals/v2", params={"key": settings.itad_api_key}, json=body
        )
        resp.raise_for_status()
        data = resp.json()

    offers = []
    for game in data.get("list", []):
        deal = game["deal"]
        assets = game.get("assets") or {}
        offers.append(
            Offer(
                source="IsThereAnyDeal",
                name=game["title"],
                price=deal["price"]["amount"],
                base_price=deal["regular"]["amount"],
                currency=deal["price"]["currency"],
                discount_percent=deal["cut"],
                url=deal["url"],
                platform=deal["shop"]["name"],
                image=assets.get("boxart") or assets.get("banner145"),
                is_dlc=game.get("type") == "dlc",
            )
        )

    # /deals/v2 ne renvoie pas de total exact ; hasMore + nextOffset servent
    # d'indicateur, on approxime le total par le nombre chargé (+1 si plus dispo)
    total = len(offers) + (1 if data.get("hasMore") else 0)
    return offers, total
