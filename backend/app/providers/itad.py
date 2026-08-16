import httpx

from ..config import settings
from ..schemas import Offer

BASE_URL = "https://api.isthereanydeal.com"


async def suggest(query: str, limit: int = 8) -> list[str]:
    if not settings.itad_api_key:
        return []

    async with httpx.AsyncClient(timeout=6) as client:
        resp = await client.get(
            f"{BASE_URL}/games/search/v1",
            params={"key": settings.itad_api_key, "title": query, "results": max(limit * 4, 30)},
        )
        resp.raise_for_status()
        games = resp.json()

    seen = set()
    titles = []
    for g in games:
        title = g["title"]
        if title.lower() not in seen:
            seen.add(title.lower())
            titles.append(title)

    q = query.strip().lower()

    def rank(title: str) -> tuple[int, int]:
        low = title.lower()
        if low.startswith(q):
            return (0, len(title))
        # match au début d'un mot ("the sims" pour "sims")
        if any(word.startswith(q) for word in low.split()):
            return (1, len(title))
        return (2, len(title))

    titles.sort(key=rank)
    return titles[:limit]


async def search(query: str) -> list[Offer]:
    if not settings.itad_api_key:
        raise RuntimeError("ITAD_API_KEY manquant")

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
            )
        )
    return offers
