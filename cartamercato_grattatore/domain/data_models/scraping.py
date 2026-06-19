from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ProductURL(BaseModel):
    """Represents a product with its associated URL for scraping."""

    product_name: str
    url: HttpUrl


class CardmarketProductInfo(BaseModel):
    """Structured product information extracted from a Cardmarket product page."""

    model_config = ConfigDict(frozen=True)

    product_name: str
    url: str
    title: str | None = None
    available_items: int | None = None
    from_price: Decimal | None = None
    price_trend: Decimal | None = None
    avg_price_30_days: Decimal | None = None
    avg_price_7_days: Decimal | None = None
    avg_price_1_day: Decimal | None = None
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
