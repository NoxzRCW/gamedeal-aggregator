from pydantic import BaseModel


class Offer(BaseModel):
    source: str
    name: str
    price: float | None = None
    base_price: float | None = None
    currency: str = "EUR"
    discount_percent: int | None = None
    url: str | None = None
    platform: str | None = None
    image: str | None = None


class BundleDeal(BaseModel):
    bundle_title: str
    bundle_url: str
    bundle_image: str | None = None
    entry_price: float
    currency: str = "EUR"
    items_count: int
    matched_item: str
    matched_item_msrp: float | None = None
    total_value: float | None = None
    end_date: str | None = None
    savings: float | None = None
    deal_type: str = "cheaper"  # "cheaper" (moins cher direct) ou "value" (rentable via la valeur globale)
    extra_cost: float | None = None
    other_items_value: float | None = None


class Bundle(BaseModel):
    machine_name: str
    title: str
    url: str
    image: str | None = None
    blurb: str | None = None
    highlights: list[str] = []
    entry_price: float | None = None
    currency: str = "EUR"
    end_date: str | None = None


class SearchResponse(BaseModel):
    query: str
    offers: list[Offer]
    bundle_deals: list[BundleDeal] = []
    errors: list[str] = []
    total: int = 0
    loaded_total: int = 0
    has_more: bool = False
