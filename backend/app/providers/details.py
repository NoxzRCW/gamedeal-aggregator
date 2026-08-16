import httpx

from ..config import settings
from .itad import _sanitize_title

ITAD_BASE = "https://api.isthereanydeal.com"
STEAM_BASE = "https://store.steampowered.com/api/appdetails"


async def get_details(title: str) -> dict | None:
    if not settings.itad_api_key:
        return None

    title = _sanitize_title(title)

    async with httpx.AsyncClient(timeout=8) as client:
        search_resp = await client.get(
            f"{ITAD_BASE}/games/search/v1",
            params={"key": settings.itad_api_key, "title": title, "results": 1},
        )
        search_resp.raise_for_status()
        matches = search_resp.json()
        if not matches:
            return None

        game_id = matches[0]["id"]
        info_resp = await client.get(
            f"{ITAD_BASE}/games/info/v2", params={"key": settings.itad_api_key, "id": game_id}
        )
        info_resp.raise_for_status()
        info = info_resp.json()

        details = {
            "title": info.get("title"),
            "release_date": info.get("releaseDate"),
            "developers": [d["name"] for d in info.get("developers", [])[:2]],
            "publishers": [p["name"] for p in info.get("publishers", [])[:2]],
            "tags": info.get("tags", []),
            "reviews": [
                {"source": r["source"], "score": r["score"], "url": r.get("url")}
                for r in info.get("reviews", [])
            ],
            "banner": (info.get("assets") or {}).get("banner600") or (info.get("assets") or {}).get("boxart"),
            "description": None,
            "genres": [],
            "categories": [],
            "screenshots": [],
            "header_image": None,
        }

        appid = info.get("appid")
        if appid:
            try:
                steam_resp = await client.get(
                    STEAM_BASE, params={"appids": appid, "l": "french", "cc": "fr"}
                )
                steam_resp.raise_for_status()
                payload = steam_resp.json().get(str(appid), {})
                if payload.get("success"):
                    data = payload["data"]
                    details["description"] = data.get("short_description")
                    details["genres"] = [g["description"] for g in data.get("genres", [])]
                    details["categories"] = [c["description"] for c in data.get("categories", [])][:6]
                    details["screenshots"] = [
                        s["path_thumbnail"] for s in data.get("screenshots", [])[:6]
                    ]
                    details["header_image"] = data.get("header_image")
            except httpx.HTTPError:
                pass

        return details
