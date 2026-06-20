"""Tests for GspreadSheetsWriter and _extract_spreadsheet_id."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from gspread.exceptions import GSpreadException
from pytest_mock import MockerFixture

from cartamercato_grattatore.domain.exceptions.google_sheets import GoogleSheetsError
from cartamercato_grattatore.infrastructure.google_sheets import (
    GspreadSheetsWriter,
    _extract_spreadsheet_id,
)


class TestExtractSpreadsheetId:
    """Tests for the _extract_spreadsheet_id helper function."""

    def test_when_valid_url_then_returns_id(self) -> None:
        """A standard Google Sheets URL should return the spreadsheet ID."""
        url = "https://docs.google.com/spreadsheets/d/1H9smJPIGldj69qU/edit?usp=sharing"
        result = _extract_spreadsheet_id(url)
        assert result == "1H9smJPIGldj69qU"

    def test_when_short_url_then_returns_id(self) -> None:
        """A URL without query params should return the spreadsheet ID."""
        url = "https://docs.google.com/spreadsheets/d/abc123"
        result = _extract_spreadsheet_id(url)
        assert result == "abc123"

    def test_when_invalid_url_then_raises(self) -> None:
        """A URL without the expected format should raise GoogleSheetsError."""
        with pytest.raises(GoogleSheetsError):
            _extract_spreadsheet_id("https://example.com/not-a-sheet")


class TestGspreadSheetsWriter:
    """Tests for GspreadSheetsWriter."""

    def test_init_when_credentials_not_found_then_raises(
        self,
    ) -> None:
        """When credentials file doesn't exist, GoogleSheetsError is raised."""
        with pytest.raises(GoogleSheetsError, match="Credentials file not found"):
            GspreadSheetsWriter(
                spreadsheet_url="https://docs.google.com/spreadsheets/d/test123",
                credentials_path=Path("/nonexistent/creds.json"),
            )

    def test_init_when_gspread_fails_then_raises(
        self,
    ) -> None:
        """When gspread fails to authenticate, GoogleSheetsError is raised."""
        with (
            patch(
                "cartamercato_grattatore.infrastructure.google_sheets.gspread.service_account"
            ) as mock_sa,
            patch(
                "cartamercato_grattatore.infrastructure.google_sheets._extract_spreadsheet_id",
                return_value="test123",
            ),
        ):
            mock_sa.side_effect = GSpreadException("auth error")

            with pytest.raises(GoogleSheetsError, match="Failed to open spreadsheet"):
                GspreadSheetsWriter(
                    spreadsheet_url="https://docs.google.com/spreadsheets/d/test123",
                    credentials_path=Path("/creds.json"),
                )

    def test_ensure_sheet_when_exists_then_no_create(
        self,
        mock_spreadsheet: MagicMock,
    ) -> None:
        """When the sheet already exists, no new sheet is created."""
        writer = GspreadSheetsWriter.__new__(GspreadSheetsWriter)
        writer._spreadsheet = mock_spreadsheet

        writer.ensure_sheet("Product A", ["Data", "Items"])

        mock_spreadsheet.add_worksheet.assert_not_called()

    def test_ensure_sheet_when_not_exists_then_creates_with_headers(
        self,
        mock_spreadsheet: MagicMock,
    ) -> None:
        """When the sheet doesn't exist, it is created with headers."""
        mock_sheet = MagicMock()
        # First call raises (sheet not found), second call returns created sheet
        mock_spreadsheet.worksheet.side_effect = [
            GSpreadException("no such sheet"),
            mock_sheet,
        ]

        writer = GspreadSheetsWriter.__new__(GspreadSheetsWriter)
        writer._spreadsheet = mock_spreadsheet

        writer.ensure_sheet("Product A", ["Data", "Items", "Price"])

        mock_spreadsheet.add_worksheet.assert_called_once_with(title="Product A", rows=1000, cols=3)
        mock_sheet.update.assert_called_once_with([["Data", "Items", "Price"]])

    def test_append_row_when_success_then_appends(
        self,
        mock_spreadsheet: MagicMock,
    ) -> None:
        """When appending succeeds, the row is written."""
        mock_sheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_sheet

        writer = GspreadSheetsWriter.__new__(GspreadSheetsWriter)
        writer._spreadsheet = mock_spreadsheet

        writer.append_row("Product A", ["2026-06-19", 10, 100.5, 105.0, 110.0])

        mock_sheet.append_row.assert_called_once_with(["2026-06-19", 10, 100.5, 105.0, 110.0])

    def test_append_row_when_fails_then_raises(
        self,
        mock_spreadsheet: MagicMock,
    ) -> None:
        """When the append operation fails, GoogleSheetsError is raised."""
        mock_sheet = MagicMock()
        mock_sheet.append_row.side_effect = GSpreadException("write failed")
        mock_spreadsheet.worksheet.return_value = mock_sheet

        writer = GspreadSheetsWriter.__new__(GspreadSheetsWriter)
        writer._spreadsheet = mock_spreadsheet

        with pytest.raises(GoogleSheetsError, match="Failed to append row"):
            writer.append_row("Product A", ["2026-06-19", 10])


@pytest.fixture
def mock_spreadsheet(mocker: MockerFixture) -> MagicMock:
    """Provide a mocked gspread Spreadsheet."""
    mock = MagicMock()
    mock_sheet = MagicMock()
    mock.worksheet.return_value = mock_sheet
    return mock
