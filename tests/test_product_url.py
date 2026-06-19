"""Tests for the ProductURL domain data model."""

import pytest
from cartamercato_grattatore.domain.data_models.scraping import ProductURL


class TestProductURL:
    """Tests for ProductURL creation and validation."""

    def test_create_product_url_when_valid_data_then_success(self) -> None:
        """Creating a ProductURL with valid data should succeed."""
        product = ProductURL(product_name="Test Product", url="https://example.com/product")

        assert product.product_name == "Test Product"
        assert str(product.url) == "https://example.com/product"

    @pytest.mark.parametrize(
        "url",
        [
            "not-a-url",
            "",
            "ftp://example.com",
            "http://",
        ],
    )
    def test_create_product_url_when_invalid_url_then_raises_validation_error(
        self, url: str
    ) -> None:
        """Creating a ProductURL with an invalid URL should raise a validation error."""
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            ProductURL(product_name="Test", url=url)
