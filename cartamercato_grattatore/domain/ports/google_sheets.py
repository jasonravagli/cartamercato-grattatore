"""Domain port for Google Sheets operations."""

from abc import ABC, abstractmethod

from overrides import EnforceOverrides


class BaseGoogleSheetsWriter(ABC, EnforceOverrides):
    """Abstract interface defining Google Sheets writing functionality."""

    @abstractmethod
    def ensure_sheet(self, sheet_name: str, headers: list[str]) -> None:
        """Create a sheet with headers if it does not already exist.

        Args:
            sheet_name: The name of the sheet (corresponds to product name).
            headers: The column headers to write if the sheet is newly created.

        Raises:
            GoogleSheetsError: If the operation fails.
        """
        pass

    @abstractmethod
    def append_row(self, sheet_name: str, values: list) -> None:
        """Append a row of values to an existing sheet.

        Args:
            sheet_name: The name of the sheet to append to.
            values: The row values to append.

        Raises:
            GoogleSheetsError: If the operation fails.
        """
        pass
