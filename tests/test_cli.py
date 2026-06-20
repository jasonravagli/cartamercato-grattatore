"""Tests for CLI argument parsing."""

from pathlib import Path

from cartamercato_grattatore.interface_adapters.cli import (
    DEFAULT_CSV_PATH,
    DEFAULT_SPREADSHEET_URL,
    parse_args,
)


class TestParseArgs:
    """Tests for CLI argument parsing."""

    def test_parse_args_when_csv_file_provided_then_returns_path(self) -> None:
        """Parsing with --csv-file should return the provided path."""
        args = parse_args(["--csv-file", "custom/path.csv"])

        assert args.csv_file == Path("custom/path.csv")

    def test_parse_args_when_no_arguments_then_returns_default_path(self) -> None:
        """Parsing without arguments should return the default path."""
        args = parse_args([])

        assert args.csv_file == DEFAULT_CSV_PATH
        assert args.csv_file == Path("assets/products.csv")

    def test_parse_args_when_google_spreadsheet_url_provided_then_returns_url(
        self,
    ) -> None:
        """Parsing with --google-spreadsheet-url should return the provided URL."""
        url = "https://docs.google.com/spreadsheets/d/custom123"
        args = parse_args(["--google-spreadsheet-url", url])

        assert args.google_spreadsheet_url == url

    def test_parse_args_when_no_google_url_then_returns_default(self) -> None:
        """Parsing without --google-spreadsheet-url should return the default."""
        args = parse_args([])

        assert args.google_spreadsheet_url == DEFAULT_SPREADSHEET_URL

    def test_parse_args_when_credentials_path_provided_then_returns_path(
        self,
    ) -> None:
        """Parsing with --google-credentials-path should return the provided path."""
        args = parse_args(["--google-credentials-path", "/path/to/creds.json"])

        assert args.google_credentials_path == Path("/path/to/creds.json")

    def test_parse_args_when_no_credentials_path_then_returns_none(self) -> None:
        """Parsing without --google-credentials-path should return None."""
        args = parse_args([])

        assert args.google_credentials_path is None
