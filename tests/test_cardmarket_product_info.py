"""Tests for the CardmarketProductInfo domain data model."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from cartamercato_grattatore.domain.data_models.scraping import CardmarketProductInfo


class TestCardmarketProductInfo:
    """Tests for CardmarketProductInfo creation and serialization."""

    def test_create_when_all_fields_provided_then_model_valid(self) -> None:
        """Creating with all fields should succeed."""
        info = CardmarketProductInfo(
            product_name="Test Card",
            url="https://cardmarket.com/product/123",
            title="Test Card - Edition 1",
            available_items=224,
            from_price=Decimal("3.00"),
            price_trend=Decimal("4.41"),
            avg_price_30_days=Decimal("5.06"),
            avg_price_7_days=Decimal("4.77"),
            avg_price_1_day=Decimal("3.73"),
        )

        assert info.product_name == "Test Card"
        assert info.available_items == 224
        assert info.from_price == Decimal("3.00")
        assert info.price_trend == Decimal("4.41")
        assert info.avg_price_30_days == Decimal("5.06")
        assert info.avg_price_7_days == Decimal("4.77")
        assert info.avg_price_1_day == Decimal("3.73")

    def test_create_when_only_required_fields_then_optionals_are_none(self) -> None:
        """Creating with required fields only should set optionals to None."""
        info = CardmarketProductInfo(
            product_name="Test",
            url="https://cardmarket.com/x",
        )

        assert info.title is None
        assert info.available_items is None
        assert info.from_price is None
        assert info.price_trend is None

    def test_model_dump_when_decimal_prices_then_returns_dict(self) -> None:
        """model_dump should serialize Decimal values correctly."""
        info = CardmarketProductInfo(
            product_name="Test",
            url="https://cardmarket.com/x",
            from_price=Decimal("3.50"),
        )

        data = info.model_dump()

        assert data["from_price"] == Decimal("3.50")

    def test_model_dump_json_when_decimal_prices_then_serializes_correctly(self) -> None:
        """model_dump_json should serialize Decimal values as strings."""
        info = CardmarketProductInfo(
            product_name="Test",
            url="https://cardmarket.com/x",
            from_price=Decimal("3.50"),
        )

        json_str = info.model_dump_json()

        assert '"from_price":"3.50"' in json_str

    def test_extracted_at_when_not_provided_then_set_to_now(self) -> None:
        """extracted_at should default to the current time."""
        before = datetime.now(UTC)
        info = CardmarketProductInfo(
            product_name="Test",
            url="https://cardmarket.com/x",
        )
        after = datetime.now(UTC)

        assert before <= info.extracted_at <= after

    def test_model_is_frozen_then_raises_on_mutation(self) -> None:
        """Model should be immutable; mutation attempts should raise."""
        info = CardmarketProductInfo(
            product_name="Test",
            url="https://cardmarket.com/x",
        )

        with pytest.raises(ValidationError):
            info.title = "Mutated"  # type: ignore[item-assigned]
