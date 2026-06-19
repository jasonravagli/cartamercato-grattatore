"""Tests for the ScrapeProducts application use case."""

from pathlib import Path
from unittest.mock import MagicMock

from cartamercato_grattatore.application.use_cases.scrape_products import ScrapeProducts
from cartamercato_grattatore.domain.exceptions.scraping import ScrapingError


class TestScrapeProducts:
    """Tests for the ScrapeProducts use case."""

    def test_load_products_when_csv_has_data_then_returns_product_urls(
        self, sample_csv: Path
    ) -> None:
        """Loading a CSV with products should return a list of ProductURL objects."""
        scraper = MagicMock()
        use_case = ScrapeProducts(scraper=scraper, serialization_dir=Path("/tmp"))

        products = use_case._load_products(sample_csv)

        assert len(products) == 2
        assert products[0].product_name == "Product A"
        assert str(products[0].url) == "https://example.com/a"
        assert products[1].product_name == "Product B"
        assert str(products[1].url) == "https://example.com/b"

    def test_load_products_when_csv_has_single_product_then_returns_one_item(
        self, single_product_csv: Path
    ) -> None:
        """Loading a CSV with one product should return a list with one item."""
        scraper = MagicMock()
        use_case = ScrapeProducts(scraper=scraper, serialization_dir=Path("/tmp"))

        products = use_case._load_products(single_product_csv)

        assert len(products) == 1
        assert products[0].product_name == "Product X"

    def test_load_products_when_csv_is_empty_then_returns_empty_list(self, empty_csv: Path) -> None:
        """Loading an empty CSV should return an empty list."""
        scraper = MagicMock()
        use_case = ScrapeProducts(scraper=scraper, serialization_dir=Path("/tmp"))

        products = use_case._load_products(empty_csv)

        assert len(products) == 0

    def test_execute_when_csv_has_valid_products_then_saves_html_files(
        self, sample_csv: Path, mock_scraper: MagicMock, serialization_dir: Path
    ) -> None:
        """Executing with valid products should save HTML files for each."""
        mock_scraper.scrape.side_effect = [
            "<html>A</html>",
            "<html>B</html>",
        ]
        use_case = ScrapeProducts(scraper=mock_scraper, serialization_dir=serialization_dir)

        use_case.execute(sample_csv)

        assert (serialization_dir / "Product A.html").exists()
        assert (serialization_dir / "Product B.html").exists()
        assert (serialization_dir / "Product A.html").read_text() == "<html>A</html>"
        assert (serialization_dir / "Product B.html").read_text() == "<html>B</html>"

    def test_execute_when_csv_is_empty_then_no_files_saved(
        self, empty_csv: Path, mock_scraper: MagicMock, serialization_dir: Path
    ) -> None:
        """Executing with an empty CSV should save no files."""
        use_case = ScrapeProducts(scraper=mock_scraper, serialization_dir=serialization_dir)

        use_case.execute(empty_csv)

        assert mock_scraper.scrape.call_count == 0
        assert list(serialization_dir.iterdir()) == []

    def test_execute_when_one_product_fails_then_skips_and_continues(
        self, sample_csv: Path, mock_scraper: MagicMock, serialization_dir: Path
    ) -> None:
        """If one product fails, it should be skipped and the rest processed."""
        mock_scraper.scrape.side_effect = [
            ScrapingError("Failed"),
            "<html>B</html>",
        ]
        use_case = ScrapeProducts(scraper=mock_scraper, serialization_dir=serialization_dir)

        use_case.execute(sample_csv)

        assert not (serialization_dir / "Product A.html").exists()
        assert (serialization_dir / "Product B.html").exists()

    def test_execute_when_called_then_closes_scraper(
        self, sample_csv: Path, mock_scraper: MagicMock, serialization_dir: Path
    ) -> None:
        """Executing should close the scraper when done."""
        use_case = ScrapeProducts(scraper=mock_scraper, serialization_dir=serialization_dir)

        use_case.execute(sample_csv)

        mock_scraper.close.assert_called_once()
