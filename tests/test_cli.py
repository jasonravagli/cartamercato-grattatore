"""Tests for CLI argument parsing."""

from pathlib import Path

from cartamercato_grattatore.interface_adapters.cli import DEFAULT_CSV_PATH, parse_args


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
