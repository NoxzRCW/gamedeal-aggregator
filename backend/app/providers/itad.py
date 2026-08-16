import httpx

from ..config import settings
from ..schemas import Offer
from ..text_utils import sanitize_title as _sanitize_title

BASE_URL = "https://api.isthereanydeal.com"


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


async def search(query: str) -> list[Offer]:
    if not settings.itad_api_key:
        raise RuntimeError("ITAD_API_KEY manquant")

    query = _sanitize_title(query)

    async with httpx.AsyncClient(timeout=10) as client:
        lookup = await client.get(
            f"{BASE_URL}/games/search/v1",
            params={"key": settings.itad_api_key, "title": query, "results": 5},
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
            )
        )
    return offers
