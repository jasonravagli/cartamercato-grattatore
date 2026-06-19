from pydantic import BaseModel, HttpUrl


class ProductURL(BaseModel):
    """Represents a product with its associated URL for scraping."""

    product_name: str
    url: HttpUrl
