"""Exceptions for Google Sheets operations."""


class GoogleSheetsError(Exception):
    """Exception raised when a Google Sheets operation fails.

    This covers authentication errors, permission denied, network failures,
    and any other Google Sheets API errors.
    """

    pass
