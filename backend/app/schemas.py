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


class SearchResponse(BaseModel):
    query: str
    offers: list[Offer]
    errors: list[str] = []
