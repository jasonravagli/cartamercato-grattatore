"""Google Sheets infrastructure implementation using gspread."""

from pathlib import Path

import gspread
from gspread import Spreadsheet
from gspread.exceptions import APIError, GSpreadException
from overrides import override

from cartamercato_grattatore.domain.exceptions.google_sheets import GoogleSheetsError
from cartamercato_grattatore.domain.ports.google_sheets import BaseGoogleSheetsWriter


def _extract_spreadsheet_id(url: str) -> str:
    """Extract the spreadsheet ID from a Google Sheets URL.

    Args:
        url: Full Google Sheets URL.

    Returns:
        The spreadsheet ID string.

    Raises:
        GoogleSheetsError: If the ID cannot be extracted.
    """
    # Format: .../spreadsheets/d/{ID}/...
    if "/spreadsheets/d/" not in url:
        raise GoogleSheetsError(f"Could not extract spreadsheet ID from URL: {url}")

    parts = url.split("/spreadsheets/d/")
    if len(parts) < 2:
        raise GoogleSheetsError(f"Could not extract spreadsheet ID from URL: {url}")

    remainder = parts[1]
    spreadsheet_id = remainder.split("/")[0]

    if not spreadsheet_id:
        raise GoogleSheetsError(f"Could not extract spreadsheet ID from URL: {url}")

    return spreadsheet_id


class GspreadSheetsWriter(BaseGoogleSheetsWriter):
    """Concrete Google Sheets writer using the gspread library."""

    def __init__(self, spreadsheet_url: str, credentials_path: Path) -> None:
        """Initialize the writer with credentials and target spreadsheet.

        Args:
            spreadsheet_url: URL of the target Google Spreadsheet.
            credentials_path: Path to the service account JSON credentials file.

        Raises:
            GoogleSheetsError: If authentication or spreadsheet access fails.
        """
        self._spreadsheet = self._open_spreadsheet(spreadsheet_url, credentials_path)

    @staticmethod
    def _open_spreadsheet(spreadsheet_url: str, credentials_path: Path) -> Spreadsheet:
        """Open the target Google Spreadsheet.

        Args:
            spreadsheet_url: URL of the spreadsheet.
            credentials_path: Path to service account JSON file.

        Returns:
            The opened Spreadsheet object.

        Raises:
            GoogleSheetsError: If authentication or opening fails.
        """
        try:
            spreadsheet_id = _extract_spreadsheet_id(spreadsheet_url)
            client = gspread.service_account(filename=credentials_path)
            return client.open_by_key(spreadsheet_id)
        except FileNotFoundError as e:
            raise GoogleSheetsError(
                f"Credentials file not found: {credentials_path}. "
                f"Set GOOGLE_APPLICATION_CREDENTIALS or pass --google-credentials-path."
            ) from e
        except (GSpreadException, OSError) as e:
            raise GoogleSheetsError(
                f"Failed to open spreadsheet: {spreadsheet_url}. "
                f"Check the URL, credentials, and that the service account has access."
            ) from e

    @override
    def ensure_sheet(self, sheet_name: str, headers: list[str]) -> None:
        """Create a sheet with headers if it does not already exist.

        Args:
            sheet_name: The name of the sheet.
            headers: The column headers to write if the sheet is new.

        Raises:
            GoogleSheetsError: If the operation fails.
        """
        try:
            sheet = self._spreadsheet.worksheet(sheet_name)
            # Sheet exists, no need to add headers
        except GSpreadException:
            # Sheet does not exist, create it with headers
            try:
                self._spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=len(headers))
                sheet = self._spreadsheet.worksheet(sheet_name)
                sheet.update([headers])
            except (GSpreadException, APIError) as e:
                raise GoogleSheetsError(f"Failed to create sheet '{sheet_name}': {e}") from e

    @override
    def append_row(self, sheet_name: str, values: list) -> None:
        """Append a row of values to an existing sheet.

        Args:
            sheet_name: The name of the sheet.
            values: The row values to append.

        Raises:
            GoogleSheetsError: If the operation fails.
        """
        try:
            sheet = self._spreadsheet.worksheet(sheet_name)
            sheet.append_row(values)
        except (GSpreadException, APIError) as e:
            raise GoogleSheetsError(f"Failed to append row to sheet '{sheet_name}': {e}") from e
