"""Tests for PublishToSheets use case."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from cartamercato_grattatore.application.use_cases.publish_to_sheets import (
    SHEET_HEADERS,
    PublishToSheets,
)
from cartamercato_grattatore.domain.exceptions.google_sheets import GoogleSheetsError


class TestPublishToSheets:
    """Tests for the PublishToSheets use case."""

    def test_execute_when_json_files_exist_then_publishes_all(
        self,
        serialization_dir: Path,
        mock_writer: MagicMock,
    ) -> None:
        """When JSON files are present, all products are published to sheets."""
        info_json = {
            "product_name": "Test Product",
            "url": "https://example.com",
            "title": "Test",
            "available_items": 10,
            "from_price": "5.00",
            "price_trend": "5.50",
            "avg_price_30_days": "100.50",
            "avg_price_7_days": "105.00",
            "avg_price_1_day": "110.00",
            "extracted_at": "2026-06-19T10:30:00+00:00",
        }
        (serialization_dir / "Test Product.json").write_text(
            json.dumps(info_json), encoding="utf-8"
        )

        publish = PublishToSheets(writer=mock_writer)
        publish.execute(serialization_dir)

        mock_writer.ensure_sheet.assert_called_once_with("Test Product", SHEET_HEADERS)
        mock_writer.append_row.assert_called_once()

    def test_execute_when_no_json_files_then_no_ops(
        self, serialization_dir: Path, mock_writer: MagicMock
    ) -> None:  # noqa: E501
        """When no JSON files exist, no sheet operations are performed."""
        publish = PublishToSheets(writer=mock_writer)
        publish.execute(serialization_dir)

        mock_writer.ensure_sheet.assert_not_called()
        mock_writer.append_row.assert_not_called()

    def test_execute_when_json_invalid_then_skipped(
        self,
        serialization_dir: Path,
        mock_writer: MagicMock,
    ) -> None:
        """When a JSON file is invalid, it is skipped and logged."""
        (serialization_dir / "Bad Product.json").write_text("not json", encoding="utf-8")

        publish = PublishToSheets(writer=mock_writer)
        publish.execute(serialization_dir)

        mock_writer.ensure_sheet.assert_not_called()
        mock_writer.append_row.assert_not_called()

    def test_execute_when_writer_fails_then_raises(
        self,
        serialization_dir: Path,
        mock_writer: MagicMock,
    ) -> None:
        """When the writer raises GoogleSheetsError, execution stops."""
        info_json = {
            "product_name": "Test Product",
            "url": "https://example.com",
            "title": "Test",
            "available_items": 10,
            "from_price": "5.00",
            "price_trend": "5.50",
            "avg_price_30_days": "100.50",
            "avg_price_7_days": "105.00",
            "avg_price_1_day": "110.00",
            "extracted_at": "2026-06-19T10:30:00+00:00",
        }
        (serialization_dir / "Test Product.json").write_text(
            json.dumps(info_json), encoding="utf-8"
        )

        mock_writer.ensure_sheet.side_effect = GoogleSheetsError("auth failed")

        publish = PublishToSheets(writer=mock_writer)

        with pytest.raises(GoogleSheetsError, match="auth failed"):
            publish.execute(serialization_dir)

    def test_build_row_when_all_fields_present_then_correct_values(
        self,
        serialization_dir: Path,
        mock_writer: MagicMock,
    ) -> None:
        """When all fields are present, the row has correct values."""
        publish = PublishToSheets(writer=mock_writer)
        info = MagicMock()
        info.extracted_at = datetime(2026, 6, 19, 10, 30, 0, tzinfo=UTC)
        info.available_items = 25
        info.avg_price_30_days = Decimal("100.50")
        info.avg_price_7_days = Decimal("105.00")
        info.avg_price_1_day = Decimal("110.00")

        row = publish._build_row(info)

        assert row == ["2026-06-19 10:30:00", 25, 100.5, 105.0, 110.0]

    def test_build_row_when_prices_null_then_empty_strings(
        self,
        serialization_dir: Path,
        mock_writer: MagicMock,
    ) -> None:
        """When price fields are None, they become empty strings in the row."""
        publish = PublishToSheets(writer=mock_writer)
        info = MagicMock()
        info.extracted_at = datetime(2026, 6, 19, 10, 30, 0, tzinfo=UTC)
        info.available_items = None
        info.avg_price_30_days = None
        info.avg_price_7_days = None
        info.avg_price_1_day = None

        row = publish._build_row(info)

        assert row == ["2026-06-19 10:30:00", "", "", "", ""]


@pytest.fixture
def mock_writer(mocker: MockerFixture) -> MagicMock:
    """Provide a mocked BaseGoogleSheetsWriter instance."""
    mock = mocker.MagicMock()
    return mock
