import json
import re

import httpx

BASE_URL = "https://www.humblebundle.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}

LANDING_JSON_RE = re.compile(
    r'<script id="landingPage-json-data" type="application/json">(.*?)</script>', re.S
)
BUNDLE_JSON_RE = re.compile(
    r'<script id="webpack-bundle-page-data" type="application/json">(.*?)</script>', re.S
)


def _money(entry: dict | None) -> float | None:
    if not entry:
        return None
    return entry.get("amount")


async def list_bundles(category: str = "games") -> list[dict]:
    async with httpx.AsyncClient(timeout=10, headers=HEADERS) as client:
        resp = await client.get(f"{BASE_URL}/bundles")
        resp.raise_for_status()
        html = resp.text

    match = LANDING_JSON_RE.search(html)
    if not match:
        return []
    data = json.loads(match.group(1))
    sections = data.get("data", {}).get(category, {}).get("mosaic", [])

    bundles = []
    seen = set()
    for section in sections:
        for product in section.get("products", []):
            if product.get("category") != "bundle":
                continue
            machine_name = product.get("machine_name")
            if not machine_name or machine_name in seen:
                continue
            seen.add(machine_name)

            entry_price = None
            for hl in product.get("hero_highlights", []):
                m = re.search(r"Pay [^\d]*([\d.,]+) or more", hl.get("heading", ""))
                if m:
                    entry_price = float(m.group(1).replace(",", "."))
                    break

            bundles.append(
                {
                    "machine_name": machine_name,
                    "title": product.get("tile_name"),
                    "url": f"{BASE_URL}{product.get('product_url', '')}",
                    "image": product.get("high_res_tile_image") or product.get("tile_image"),
                    "blurb": re.sub(r"<[^>]+>", "", product.get("marketing_blurb", "")),
                    "highlights": product.get("highlights", []),
                    "entry_price": entry_price,
                    "currency": "EUR",
                    "end_date": product.get("end_date|datetime"),
                }
            )
    return bundles


async def get_bundle_detail(product_url_path: str) -> dict | None:
    async with httpx.AsyncClient(timeout=10, headers=HEADERS) as client:
        resp = await client.get(f"{BASE_URL}{product_url_path}")
        if resp.status_code != 200:
            return None
        html = resp.text

    match = BUNDLE_JSON_RE.search(html)
    if not match:
        return None

    try:
        data = json.loads(match.group(1))
        bd = data["bundleData"]
        pricing = bd.get("tier_pricing_data", {})
        initial = pricing.get("initial") or next(iter(pricing.values()), {})
        entry_price = _money(initial.get("price|money"))

        items = []
        for item in bd.get("tier_item_data", {}).values():
            if item.get("item_content_type") != "game":
                continue
            items.append(
                {
                    "name": item.get("human_name"),
                    "msrp": _money(item.get("msrp_price|money")),
                }
            )
        return {"entry_price": entry_price, "items": items}
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


async def build_deal_index(max_bundles: int = 20) -> dict:
    """Construit un index {titre en minuscule: [deals]} en croisant tous les bundles jeux actifs."""
    import asyncio

    bundles = await list_bundles("games")
    bundles = bundles[:max_bundles]

    details = await asyncio.gather(
        *[get_bundle_detail(b["url"].replace(BASE_URL, "")) for b in bundles],
        return_exceptions=True,
    )

    index: dict[str, list[dict]] = {}
    for bundle, detail in zip(bundles, details):
        if not isinstance(detail, dict) or not detail.get("entry_price"):
            continue
        for item in detail["items"]:
            name = item.get("name")
            if not name:
                continue
            key = name.lower()
            index.setdefault(key, []).append(
                {
                    "bundle_title": bundle["title"],
                    "bundle_url": bundle["url"],
                    "bundle_image": bundle["image"],
                    "entry_price": detail["entry_price"],
                    "currency": "EUR",
                    "items_count": len(detail["items"]),
                    "matched_item": name,
                    "matched_item_msrp": item.get("msrp"),
                    "end_date": bundle["end_date"],
                }
            )
    return index


def find_in_index(index: dict, query: str) -> list[dict]:
    q = query.lower().strip()
    if not q:
        return []
    matches = []
    for key, deals in index.items():
        if q in key or key in q:
            matches.extend(deals)
    return matches
